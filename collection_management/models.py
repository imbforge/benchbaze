# -*- coding: utf-8 -*-

from __future__ import unicode_literals

#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.db import models
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.utils.encoding import force_text

from formz.models import ZkbsPlasmid
from formz.models import FormZBaseElement

#################################################
#        ADDED FUNCTIONALITIES IMPORTS          #
#################################################

from simple_history.models import HistoricalRecords
import os
import time

#################################################
#                CUSTOM CLASSES                 #
#################################################

class SaveWithoutHistoricalRecord():
    """Allows inheritance of method to save a object without
    saving a historical record"""

    def save_without_historical_record(self, *args, **kwargs):
        self.skip_history_when_saving = True
        try:
            ret = self.save(*args, **kwargs)
        finally:
            del self.skip_history_when_saving
        return ret

#################################################
#         SA. CEREVISIAE STRAIN MODEL           #
#################################################

mating_type_choice = (
    ('a','a'),
    ('alpha','alpha'),
    ('unknown','unknown'),
    ('a/a','a/a'),
    ('alpha/alpha','alpha/alpha'),
    ('a/alpha','a/alpha')   
)

class SaCerevisiaeStrain (models.Model):
    name = models.CharField("name", max_length = 255, blank=False)
    relevant_genotype = models.CharField("relevant genotype", max_length = 255, blank=False)
    mating_type = models.CharField("mating type", choices = mating_type_choice, max_length = 20, blank=True)
    chromosomal_genotype = models.TextField("chromosomal genotype", blank=True)
    parent_1 = models.ForeignKey('self', verbose_name = 'Parent 1', on_delete=models.PROTECT, related_name='parent_strain_1', help_text='Main parental strain', blank=True, null=True)
    parent_2 = models.ForeignKey('self', verbose_name = 'Parent 2', on_delete=models.PROTECT, related_name='parent_strain_2', help_text='Only for crosses', blank=True, null=True)
    parental_strain = models.CharField("parental strain", help_text = "Use only when 'Parent 1' does not apply", max_length = 255, blank=True)
    construction = models.TextField("construction", blank=True)
    modification = models.CharField("modification", max_length = 255, blank=True)
    integrated_plasmids = models.ManyToManyField('HuPlasmid', related_name='integrated_pl', blank= True)
    cassette_plasmids = models.ManyToManyField('HuPlasmid', related_name='cassette_pl', help_text= 'Tagging and knock out plasmids', blank= True)
    plasmids = models.CharField("plasmids", max_length = 255, help_text = 'Use only when the other plasmid fields do not apply', blank=True)
    selection = models.CharField("selection", max_length = 255, blank=True)
    phenotype = models.CharField("phenotype", max_length = 255, blank=True)
    background = models.CharField("background", max_length = 255, blank=True)
    received_from = models.CharField("received from", max_length = 255, blank=True)
    us_e = models.CharField("use", max_length = 255, blank=True)
    note = models.CharField("note", max_length = 255, blank=True)
    reference = models.CharField("reference", max_length = 255, blank=True)
    
    created_date_time = models.DateTimeField("created", auto_now_add=True)
    created_approval_by_pi = models.BooleanField("record creation approval", default = False)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    last_changed_approval_by_pi = models.NullBooleanField("record change approval", default = None)
    approval_by_pi_date_time = models.DateTimeField(null = True, default = None)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    history = HistoricalRecords()
    
    class Meta:
        '''Set a custom name to be used throughout the admin pages'''
        
        verbose_name = 'strain - Sa. cerevisiae'
        verbose_name_plural = 'strains - Sa. cerevisiae'
    
    def __str__(self):
        '''Set what to show as an object's unicode attribute, in this case
        it is just the ID of the object, but it could be its name'''
        
        return "{} - {}".format(self.id, self.name)

#################################################
#               HU PLASMID MODEL                #
#################################################

class HuPlasmid (models.Model, SaveWithoutHistoricalRecord):
    name = models.CharField("name", max_length = 255, unique=True, blank=False)
    other_name = models.CharField("other name", max_length = 255, blank=True)
    parent_vector = models.CharField("parent vector", max_length = 255, blank=True)
    selection = models.CharField("selection", max_length = 50, blank=False)
    us_e = models.CharField("use", max_length = 255, blank=True)
    construction_feature = models.TextField("construction/features", blank=True)
    received_from = models.CharField("received from", max_length = 255, blank=True)
    note = models.CharField("note", max_length = 300, blank=True)
    reference = models.CharField("reference", max_length = 255, blank=True)
    plasmid_map = models.FileField("plasmid map (max. 2 MB)", upload_to="collection_management/huplasmid/dna/", blank=True)
    plasmid_map_png = models.ImageField("plasmid image" , upload_to="collection_management/huplasmid/png/", blank=True)
    plasmid_map_gbk = models.FileField("plasmid map (.gbk)", upload_to="collection_management/huplasmid/gb/", blank=True)

    created_date_time = models.DateTimeField("created", auto_now_add=True)
    created_approval_by_pi = models.BooleanField("record creation approval", default = False)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    last_changed_approval_by_pi = models.NullBooleanField("record change approval", default = None)
    approval_by_pi_date_time = models.DateTimeField(null = True, default = None)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    history = HistoricalRecords()

    vector_known_zkbs = models.NullBooleanField("backbone in ZKBS database?", default = None, blank=True, null=True)
    vector_zkbs = models.ForeignKey(ZkbsPlasmid, verbose_name = 'ZKBS database vector', on_delete=models.PROTECT, blank=True, null=True)
    formz_elements = models.ManyToManyField(FormZBaseElement, verbose_name = 'Elements', blank=True)
    
    class Meta:
        '''Set a custom name to be used throughout the admin pages'''
        
        verbose_name = 'plasmid'
        verbose_name_plural = 'plasmids'

    def clean(self):
        """Check if file is bigger than 2 MB"""
    
        errors = []
        
        limit = 2 * 1024 * 1024
        if self.plasmid_map:
            if self.plasmid_map.size > limit:
                errors.append(ValidationError('Plasmid map too large. Size cannot exceed 2 MB.'))
        
            try:
                plasmid_map_ext = self.plasmid_map.name.split('.')[-1].lower()
            except:
                plasmid_map_ext = None
            if plasmid_map_ext == None or plasmid_map_ext != 'dna':
                errors.append(ValidationError('Invalid file format. Please select a valid SnapGene .dna file'))

        if len(errors) > 0:
            raise ValidationError(errors)

    def __str__(self):
        return "{} - {}".format(self.id, self.name)

#################################################
#                 OLIGO MODEL                   #
#################################################

class Oligo (models.Model):
    name = models.CharField("name", max_length = 255, unique = True, blank=False)
    sequence = models.CharField("sequence", max_length = 255, unique = True, blank=False)
    length = models.SmallIntegerField("length", null=True, blank=True)
    us_e = models.CharField("use", max_length = 255, blank=True)
    gene = models.CharField("gene", max_length = 255, blank=True)
    restriction_site = models.CharField("restriction sites", max_length = 255, blank=True)
    description = models.TextField("description", blank=True)
    comment = models.CharField("comments", max_length = 255, blank=True)
    
    created_date_time = models.DateTimeField("created", auto_now_add=True)
    created_approval_by_pi = models.BooleanField("record creation approval", default = False)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    last_changed_approval_by_pi = models.NullBooleanField("record change approval", default = None)
    approval_by_pi_date_time = models.DateTimeField(null = True, default = None)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    history = HistoricalRecords()
    
    def __str__(self):
       return str(self.id)

    def save(self, force_insert=False, force_update=False):
        """Automatically capitalize the sequence of an oligo and remove all white spaces
        from it. Also set the lenght of the oligo"""
        
        upper_sequence = self.sequence.upper()
        self.sequence = "".join(upper_sequence.split())
        self.length = len(self.sequence)
        super(Oligo, self).save(force_insert, force_update)

#################################################
#            SC. POMBE STRAIN MODEL             #
#################################################

class ScPombeStrain (models.Model):
    box_number = models.SmallIntegerField("box number", blank=False)
    parental_strain = models.CharField("parental strains", max_length = 255, blank=True)
    mating_type = models.CharField("mating type", max_length = 20, blank=True)
    auxotrophic_marker = models.CharField("auxotrophic markers", max_length = 255, blank=True)
    name = models.TextField("genotype", blank=False)
    phenotype = models.CharField("phenotype", max_length = 255, blank=True)
    received_from = models.CharField("received from", max_length = 255, blank=True)
    comment = models.CharField("comments", max_length = 300, blank=True)
    
    created_date_time = models.DateTimeField("created", auto_now_add=True)
    created_approval_by_pi = models.BooleanField("record creation approval", default = False)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    last_changed_approval_by_pi = models.NullBooleanField("record change approval", default = None)
    approval_by_pi_date_time = models.DateTimeField(null = True, default = None)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = 'strain - Sc. pombe'
        verbose_name_plural = 'strains - Sc. pombe'
    
    def __str__(self):
        return str(self.id)

#################################################
#                NZ PLASMID MODEL               #
#################################################

class NzPlasmid (models.Model, SaveWithoutHistoricalRecord):
    name = models.CharField("name", max_length = 255, blank=False)
    other_name = models.CharField("other name", max_length = 255, blank=True)
    parent_vector = models.CharField("parent vector", max_length = 255, blank=True)
    selection = models.CharField("selection", max_length = 50, blank=False)
    us_e = models.CharField("use", max_length = 255, blank=True)
    construction_feature = models.TextField("construction/Features", blank=True)
    received_from = models.CharField("received from", max_length = 255, blank=True)
    note = models.CharField("Note", max_length = 300, blank=True)
    reference = models.CharField("reference", max_length = 255, blank=True)
    plasmid_map = models.FileField("plasmid map (max. 2 MB)", upload_to="collection_management/nzplasmid/", blank=True)
    
    created_date_time = models.DateTimeField("created", auto_now_add=True)
    created_approval_by_pi = models.BooleanField("record creation approval", default = False)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    last_changed_approval_by_pi = models.NullBooleanField("record change approval", default = None)
    approval_by_pi_date_time = models.DateTimeField(null = True, default = None)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    history = HistoricalRecords()

    def clean(self): 
        """Check if file is bigger than 2 MB"""
        
        errors = []
        
        limit = 2 * 1024 * 1024
        if self.plasmid_map:
            if self.plasmid_map.size > limit:
                errors.append(ValidationError('Plasmid map too large. Size cannot exceed 2 MB.'))
        
            try:
                plasmid_map_ext = self.plasmid_map.name.split('.')[-1].lower()
            except:
                plasmid_map_ext = None
            if plasmid_map_ext == None or plasmid_map_ext != 'dna':
                errors.append(ValidationError('Invalid file format. Please select a valid SnapGene .dna file'))

        if len(errors) > 0:
            raise ValidationError(errors)
    
    class Meta:
        verbose_name = "nicola's plasmid"
        verbose_name_plural = "nicola's plasmids"
        
    def __str__(self):
        return str(self.id)

#################################################
#              E. COLI STRAIN MODEL             #
#################################################

class EColiStrain (models.Model):
    name = models.CharField("name", max_length = 255, blank=False)
    resistance = models.CharField("resistance", max_length = 255, blank=True)
    genotype = models.TextField("genotype", blank=True)
    supplier = models.CharField("supplier", max_length = 255, blank=True)
    us_e = models.CharField("use", max_length = 255, choices=(('Cloning', 'Cloning'),('Expression', 'Expression'),('Other', 'Other'),))
    purpose = models.TextField("purpose", blank=True)
    note =  models.CharField("note", max_length = 255, blank=True)
    
    created_date_time = models.DateTimeField("created", auto_now_add=True)
    created_approval_by_pi = models.BooleanField("record creation approval", default = False)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    last_changed_approval_by_pi = models.NullBooleanField("record change approval", default = None)
    approval_by_pi_date_time = models.DateTimeField(null = True, default = None)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = 'strain - E. coli'
        verbose_name_plural = 'strains - E. coli'
        
    def __str__(self):
       return str(self.id)

################################################
#         MAMMALIAN CELL LINE MODEL            #
################################################

class MammalianLine (models.Model):
    name = models.CharField("name", max_length = 255, unique=True, blank=False)
    box_name = models.CharField("box", max_length = 255, blank=False)
    alternative_name = models.CharField("alternative name", max_length = 255, blank=True)
    parental_line_old = models.CharField("parental cell line", max_length = 255, blank=False)
    parental_line = models.ForeignKey('self', on_delete=models.PROTECT, verbose_name = 'parental line', blank=True, null=True)
    organism = models.CharField("organism", max_length = 20, blank=True)
    cell_type_tissue = models.CharField("cell type/tissue", max_length = 255, blank=True)
    culture_type = models.CharField("culture type", max_length = 255, blank=True)
    growth_condition = models.CharField("growth conditions", max_length = 255, blank=True)
    freezing_medium = models.CharField("freezing medium", max_length = 255, blank=True)
    received_from = models.CharField("received from", max_length = 255, blank=True)
    description_comment = models.TextField("description/comments", blank=True)
    
    created_date_time = models.DateTimeField("created", auto_now_add=True)
    created_approval_by_pi = models.BooleanField("record creation approval", default = False)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    last_changed_approval_by_pi = models.NullBooleanField("record change approval", default = None)
    approval_by_pi_date_time = models.DateTimeField(null = True, default = None)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = 'mammmalian cell line'
        verbose_name_plural = 'mammmalian cell lines'
    
    def __str__(self):
        return "{} - {}".format(self.id, self.name)

################################################
#        MAMMALIAN CELL LINE DOC MODEL         #
################################################

class MammalianLineDoc(models.Model):
    name = models.FileField("file name", upload_to="temp/", blank=False)
    typ_e = models.CharField("doc type", max_length=255, choices=[["virus", "Virus test"], ["mycoplasma", "Mycoplasma test"], ["fingerprint", "Fingerprinting"], ["other", "Other"]], blank=False)
    date_of_test = models.DateField("date of test", blank=False)
    comment = models.CharField("comment", max_length=150, blank=True)
    mammalian_line = models.ForeignKey(MammalianLine, on_delete=models.PROTECT)
    
    created_date_time = models.DateTimeField("created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("last Changed", auto_now=True)
    
    RENAME_FILES = {
        'name': 
        {'dest': 'collection_management/mammalianlinedoc/', 'keep_ext': True}
        }

    def save(self, force_insert=False, force_update=False):
        '''Override default save method to rename a file 
        of any given name to mclHU_date-uploaded_time-uploaded.yyy,
        after the corresponding entry has been created'''
        
        rename_files = getattr(self, 'RENAME_FILES', None)
        if rename_files:
            super(MammalianLineDoc, self).save(force_insert, force_update)
            force_insert, force_update = False, True
            for field_name, options in rename_files.items():
                field = getattr(self, field_name)
                if field:
                    file_name = force_text(field)
                    name, ext = os.path.splitext(file_name)
                    ext = ext.lower()
                    keep_ext = options.get('keep_ext', True)
                    final_dest = options['dest']
                    if callable(final_dest):
                        final_name = final_dest(self, file_name)
                    else:
                        final_name = os.path.join(final_dest, "mclHU" + str(self.mammalian_line.id) + "_" + self.typ_e + "_" + time.strftime("%Y%m%d") + "_" + time.strftime("%H%M%S") + "_" + str(self.id))
                        if keep_ext:
                            final_name += ext
                    if file_name != final_name:
                        field.storage.delete(final_name)
                        field.storage.save(final_name, field)
                        field.close()
                        field.storage.delete(file_name)
                        setattr(self, field_name, final_name)
        super(MammalianLineDoc, self).save(force_insert, force_update)

    class Meta:
        verbose_name = 'mammalian cell line document'
    
    def __str__(self):
         return str(self.id)

    def clean(self):
        """Check if file is bigger than 2 MB"""

        errors = []
        
        limit = 2 * 1024 * 1024
        if self.name:
            if self.name.size > limit:
                errors.append(ValidationError('File too large. Size cannot exceed 2 MB.'))
            try:
                file_ext = self.name.name.split('.')[-1].lower()
            except:
                errors.append(ValidationError('Invalid file format. File does not have an extension'))

        if len(errors) > 0:
            raise ValidationError(errors)

#################################################
#                ANTIBODY MODEL                 #
#################################################

class Antibody (models.Model, SaveWithoutHistoricalRecord):
    name = models.CharField("name", max_length = 255, blank=False)
    species_isotype = models.CharField("species/isotype", max_length = 255, blank=False)
    clone = models.CharField("clone", max_length = 255, blank=True)
    received_from = models.CharField("receieved from", max_length = 255, blank=True)
    catalogue_number = models.CharField("catalogue number", max_length = 255, blank=True)
    l_ocation = models.CharField("location", max_length = 255, blank=True)
    a_pplication = models.CharField("application", max_length = 255, blank=True)
    description_comment = models.TextField("description/comments", blank=True)
    info_sheet = models.FileField("info sheet (max. 2 MB)", upload_to="collection_management/antibody/", blank=True)

    created_date_time = models.DateTimeField("created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    history = HistoricalRecords()

    def clean(self):
        """Check if file is bigger than 2 MB"""

        errors = []
        
        limit = 2 * 1024 * 1024
        if self.info_sheet:
            if self.info_sheet.size > limit:
                errors.append(ValidationError('File too large. Size cannot exceed 2 MB.'))
            try:
                info_sheet_ext = self.info_sheet.name.split('.')[-1].lower()
            except:
                info_sheet_ext = None
            if info_sheet_ext == None or info_sheet_ext != 'pdf':
                errors.append(ValidationError('Invalid file format. Please select a valid .pdf file'))

        if len(errors) > 0:
            raise ValidationError(errors)
    
    class Meta:
        verbose_name = 'antibody'
        verbose_name_plural = 'antibodies'
    
    def __str__(self):
        return str(self.id)