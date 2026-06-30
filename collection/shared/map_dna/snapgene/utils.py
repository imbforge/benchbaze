import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import zmq
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import mail_admins
from django.db.models.functions import Collate

from collection.models import Oligo
from .pyclasses.client import Client
from .pyclasses.config import Config

User = get_user_model()
BASE_DIR = settings.BASE_DIR
LAB_ABBREVIATION_FOR_FILES = getattr(settings, "LAB_ABBREVIATION_FOR_FILES", "")
SNAPGENE_COMMON_FEATURES_PATH = os.path.join(
    BASE_DIR, "collection/shared/map_dna/snapgene/standardCommonFeatures.ftrs"
)


def connect_snapgene_server():
    """Create SnapGene client"""

    config = Config()
    server_ports = config.get_server_ports()
    client = None

    for port in server_ports.values():
        try:
            client = Client(port, zmq.Context())
        except Exception:
            continue
        else:
            break

    if not client:
        raise Exception("Could not connect to SnapGene Server")

    return client


def mail_snapgene_error(map_path, messages):
    mail_admins(
        "Snapgene server error",
        "There was an error with creating the preview"
        f"for {map_path} with snapgene server.\n\n"
        f"Errors: {messages}.",
        fail_silently=True,
    )


def create_map_preview(
    obj, detect_common_features, attempt_number=3, messages=None, **kwargs
):
    """For a .dna map, use SnapGene server to 1) detect common features,
    2) create a .png preview of the .dna file, and 3) create a .gbk map"""

    messages = messages or []

    if attempt_number > 0:
        try:
            client = connect_snapgene_server()

            # Detect common features
            if detect_common_features:
                argument = {
                    "request": "detectFeatures",
                    "inputFile": obj.map.path,
                    "outputFile": obj.map.path,
                    "featureDatabase": SNAPGENE_COMMON_FEATURES_PATH,
                }
                r = client.requestResponse(argument, 10000)
                r_code = r.get("code", 1)
                if r_code > 0:
                    error_message = f"detectFeatures - error {r_code}"
                    if error_message not in messages:
                        messages.append(error_message)
                    client.close()
                    raise Exception

            # Create a .png preview of the .dna map
            argument = {
                "request": "generatePNGMap",
                "inputFile": obj.map.path,
                "outputPng": obj.map_png.path,
                "title": (
                    kwargs["prefix"]
                    if "prefix" in kwargs
                    else f"{obj._model_abbreviation}{LAB_ABBREVIATION_FOR_FILES}"
                    f"{obj.id} - {obj.name}"
                ),
                "showEnzymes": True,
                "showFeatures": True,
                "showPrimers": True,
                "showORFs": False,
            }
            r = client.requestResponse(argument, 10000)
            r_code = r.get("code", 1)
            if r_code > 0:
                error_message = f"generatePNGMap - error {r_code}"
                if error_message not in messages:
                    messages.append(error_message)
                client.close()
                raise Exception

            # Create a .gbk map
            argument = {
                "request": "exportDNAFile",
                "inputFile": obj.map.path,
                "outputFile": obj.map_gbk.path,
                "exportFilter": "biosequence.gb",
            }
            r = client.requestResponse(argument, 10000)
            r_code = r.get("code", 1)
            if r_code > 0:
                error_message = f"exportDNAFile - error {r_code}"
                if error_message not in messages:
                    messages.append(error_message)
                client.close()
                raise Exception

            client.close()

        except Exception:
            create_map_preview(
                obj, detect_common_features, attempt_number - 1, messages, **kwargs
            )

    else:
        mail_snapgene_error(obj.map.path, messages)
        raise Exception


def get_map_features(obj, attempt_number=3, messages=None):
    """For a .dna  map, use SnapGene server to get its
    features, as json"""

    messages = messages or []

    if attempt_number > 0:
        try:
            client = connect_snapgene_server()

            # Get features
            argument = {"request": "reportFeatures", "inputFile": obj.map.path}
            r = client.requestResponse(argument, 10000)
            r_code = r.get("code", 1)
            if r_code > 0:
                error_message = f"reportFeatures - error {r_code}"
                if error_message not in messages:
                    messages.append(error_message)
                client.close()
                raise Exception

            client.close()

            plasmid_features = r.get("features", [])
            feature_names = [feat["name"].strip() for feat in plasmid_features]
            return feature_names

        except Exception:
            get_map_features(obj, attempt_number - 1, messages)

    else:
        mail_snapgene_error(obj, messages)
        raise Exception


def convert_map_gbk_to_dna(gbk_map_path, dna_map_path, attempt_number=3, messages=None):
    """For a gbk  map (.gbk), use SnapGene server
    to convert it to .dna"""

    messages = messages or []

    if attempt_number > 0:
        try:
            client = connect_snapgene_server()

            # Convert .dna to .gbk
            argument = {
                "request": "importDNAFile",
                "inputFile": gbk_map_path,
                "outputFile": dna_map_path,
            }
            r = client.requestResponse(argument, 10000)
            r_code = r.get("code", 1)
            if r_code > 0:
                error_message = f"importDNAFile - error {r_code}"
                if error_message not in messages:
                    messages.append(error_message)
                client.close()
                raise Exception

            client.close()

        except Exception:
            convert_map_gbk_to_dna(
                gbk_map_path, dna_map_path, attempt_number - 1, messages
            )

    else:
        mail_snapgene_error(gbk_map_path, messages)
        raise Exception


def find_oligos_in_map_snapgene(map_dna_path, attempt_number=3, messages=None):
    """Given a path to a plasmid map, use snapegene server to find oligos in the map"""

    messages = messages or []
    file_format = Path(map_dna_path).suffix.lower()

    if attempt_number > 0:
        try:
            client = connect_snapgene_server()

            with (
                NamedTemporaryFile(mode="w+") as oligos_json_file,
                NamedTemporaryFile(mode="w+b") as dna_from_gbk_temp_file,
                NamedTemporaryFile(mode="w+b") as dna_out_temp_file,
            ):
                if not Oligo.objects.exists():
                    raise Exception("No oligos found in database")

                # Get all oligos with valid sequences (only A, T, C, G) and length >= 15
                oligos = (
                    Oligo.objects.annotate(
                        sequence_deterministic=Collate("sequence", "und-x-icu")
                    )
                    .filter(sequence_deterministic__iregex=r"^[ATCG]+$", length__gte=15)
                    .values_list("id", "sequence")
                )

                # Format oligos for SnapGene server
                oligos = [
                    {
                        "Name": f"! o{LAB_ABBREVIATION_FOR_FILES}{oligo_id}",
                        "Sequence": sequence,
                        "Notes": "",
                    }
                    for oligo_id, sequence in oligos
                ]

                if not oligos:
                    raise Exception("No valid oligos found in database")

                # Write oligos to temporary JSON file
                # Flush and sync the file to ensure it's written to disk before sending to SnapGene server
                json.dump(oligos, oligos_json_file)
                oligos_json_file.flush()
                os.fsync(oligos_json_file.fileno())

                # For .gb or .gbk maps, convert to .dna first
                if file_format in [".gb", ".gbk"]:
                    convert_map_gbk_to_dna(
                        map_dna_path, dna_from_gbk_temp_file.name, 3, messages
                    )
                    map_dna_path = dna_from_gbk_temp_file.name

                # Send request to SnapGene server to find primers from the list of oligos
                argument = {
                    "request": "importPrimersFromList",
                    "inputFile": str(map_dna_path),
                    "inputPrimersFile": oligos_json_file.name,
                    "outputFile": dna_out_temp_file.name,
                }
                r = client.requestResponse(argument, 60000)
                r_code = r.get("code", 1)
                if r_code > 0:
                    error_message = f"importPrimersFromList - error {r_code}"
                    if error_message not in messages:
                        messages.append(error_message)
                    client.close()
                    raise Exception(error_message)

                client.close()

                # Read the output .dna file from the temporary file and return it
                dna_out_temp_file.seek(0)
                return dna_out_temp_file.read()

        except Exception:
            return find_oligos_in_map_snapgene(
                map_dna_path, attempt_number - 1, messages
            )

    else:
        mail_snapgene_error(map_dna_path, messages)
        raise Exception
