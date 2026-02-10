from django.contrib.admin import helpers
from django.contrib.admin.utils import unquote
from django.contrib.contenttypes.admin import GenericInlineModelAdmin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models.fields.files import FieldFile, FileField
from django.forms.formsets import all_valid
from django.forms.models import model_to_dict
from django.http import Http404
from django.utils.encoding import force_str as force_text
from django.utils.html import escape
from django.utils.translation import gettext as _
from modelclone import ClonableModelAdmin
from modelclone.admin import InlineAdminFormSetFakeOriginal


class CustomClonableModelAdmin(ClonableModelAdmin):
    clone_ignore_fields = []
    add_view_fieldsets = []
    change_form_template = None
    obj_unmodifiable_fields = []

    def clone_view(self, request, object_id, form_url="", extra_context=None):
        self.fieldsets = self.add_view_fieldsets.copy()
        self.readonly_fields = self.set_readonly_fields + self.obj_unmodifiable_fields

        opts = self.model._meta

        if not self.has_add_permission(request):
            raise PermissionDenied

        original_obj = self.get_object(request, unquote(object_id))

        if original_obj is None:
            raise Http404(
                _(
                    "{name} object with primary key {key} does not exist.".format(
                        name=force_text(opts.verbose_name), key=repr(escape(object_id))
                    )
                )
            )

        ModelForm = self.get_form(request)
        formsets = []

        # Handle POST request - validate form and formsets, save new object and related objects
        if request.method == "POST":
            form = ModelForm(request.POST, request.FILES)
            if form.is_valid():
                new_object = self.save_form(request, form, change=False)
                form_validated = True
            else:
                new_object = self.model()
                form_validated = False

            prefixes = {}

            for FormSet, inline in self.get_formsets_with_inlines(request):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1 or not prefix:
                    prefix = "{}-{}".format(prefix, prefixes[prefix])

                request_files = request.FILES

                # Check if this is a GenericInlineModelAdmin (generic foreign key)
                # If so, we need to filter the inlined objects by content_type and object_id
                if isinstance(inline, GenericInlineModelAdmin):
                    ct = ContentType.objects.get_for_model(self.model)
                    inlined_objs = inline.model.objects.filter(
                        content_type=ct, object_id=original_obj.pk
                    )
                # Otherwise, we can filter by the foreign key field
                else:
                    filter_params = {
                        "%s__pk"
                        % inline.model._inline_foreignkey_fieldname: original_obj.pk
                    }
                    inlined_objs = inline.model.objects.filter(**filter_params)

                # For each inlined object, check if it has any file fields and if so, add them to
                # request.FILES so that they are saved correctly when the formset is saved
                for n, inlined_obj in enumerate(inlined_objs.all()):
                    for field in inlined_obj._meta.fields:
                        if isinstance(field, FileField) and field not in request_files:
                            value = field.value_from_object(inlined_obj)
                            file_field_name = "{}-{}-{}".format(prefix, n, field.name)
                            request_files.setdefault(file_field_name, value)

                formset = FormSet(
                    data=request.POST,
                    files=request_files,
                    instance=new_object,
                    save_as_new="_saveasnew" in request.POST,  # ????
                    prefix=prefix,
                )
                formsets.append(formset)

            if all_valid(formsets) and form_validated:
                # If original model has any file field, save new model
                # with same paths to these files
                for name in vars(original_obj):
                    field = getattr(original_obj, name)
                    if isinstance(field, FieldFile) and name not in request.FILES:
                        setattr(new_object, name, field)

                self.save_model(request, new_object, form, False)
                self.save_related(request, form, formsets, False)
                try:
                    self.log_addition(request, new_object)
                except TypeError:
                    # In Django 1.9 we need one more param
                    self.log_addition(request, new_object, "Cloned object")

                return self.response_add(request, new_object, None)

        # Handle GET request - populate form and formsets with data from original object
        else:
            initial = model_to_dict(original_obj)
            initial = self.tweak_cloned_fields(initial)
            form = ModelForm(initial=initial)

            prefixes = {}
            for FormSet, inline in self.get_formsets_with_inlines(request):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1 or not prefix:
                    prefix = "{}-{}".format(prefix, prefixes[prefix])
                initial = []

                # Check if this is a GenericInlineModelAdmin (generic foreign key)
                if isinstance(inline, GenericInlineModelAdmin):
                    # For generic relations, filter by content_type and object_id
                    ct = ContentType.objects.get_for_model(self.model)
                    queryset = inline.get_queryset(request).filter(
                        content_type=ct, object_id=original_obj.pk
                    )
                    exclude_fields = [
                        inline.model._meta.pk.name,
                        "content_type",
                        "object_id",
                    ]
                else:
                    # For regular foreign key relations
                    # Get the foreign key field name from the inline
                    if inline.fk_name:
                        fk_name = inline.fk_name
                    else:
                        # Find the foreign key field by inspecting the model
                        fk_name = None
                        for field in inline.model._meta.get_fields():
                            if field.is_relation and field.related_model == self.model:
                                fk_name = field.name
                                break
                        if fk_name is None:
                            # Fallback to the default approach
                            fk_name = self.model._meta.model_name

                    queryset = inline.get_queryset(request).filter(
                        **{fk_name: original_obj}
                    )
                    exclude_fields = [inline.model._meta.pk.name, fk_name]

                for obj in queryset:
                    initial.append(model_to_dict(obj, exclude=exclude_fields))
                initial = self.tweak_cloned_inline_fields(prefix, initial)
                formset = FormSet(prefix=prefix, initial=initial)

                # Since there is no way to customize the `extra` in the constructor,
                # construct the forms again...
                # most of this view is a hack, but this is the ugliest one
                formset.extra = len(initial) + formset.extra
                # _construct_forms() was removed on django 1.6
                # see https://github.com/django/django/commit/ef79582e8630cb3c119caed52130c9671188addd
                if hasattr(formset, "_construct_forms"):
                    formset._construct_forms()
                formsets.append(formset)

        admin_form = helpers.AdminForm(
            form,
            list(self.get_fieldsets(request)),
            self.get_prepopulated_fields(request),
            self.get_readonly_fields(request),
            model_admin=self,
        )
        media = self.media + admin_form.media

        inline_admin_formsets = []
        for inline, formset in zip(self.get_inline_instances(request), formsets):
            # Filter out inlines that should be ignored during clone view
            if getattr(inline, "clone_ignore", False):
                continue

            fieldsets = list(inline.get_fieldsets(request, original_obj))
            readonly = list(inline.get_readonly_fields(request, original_obj))
            prepopulated = dict(inline.get_prepopulated_fields(request, original_obj))
            inline_admin_formset = InlineAdminFormSetFakeOriginal(
                inline, formset, fieldsets, prepopulated, readonly, model_admin=self
            )
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media

        title = "{} {}".format(self.clone_verbose_name, opts.verbose_name)

        context = {
            "title": title,
            "original": title,
            "adminform": admin_form,
            "is_popup": "_popup" in getattr(request, "REQUEST", request.GET),
            "show_delete": False,
            "media": media,
            "inline_admin_formsets": inline_admin_formsets,
            "errors": helpers.AdminErrorList(form, formsets),
            "app_label": opts.app_label,
        }

        context.update(extra_context or {})

        # Enable navbar
        context.update({"is_nav_sidebar_enabled": True})
        context.update(self.admin_site.each_context(request))

        return self.render_change_form(
            request, context, form_url=form_url, change=False
        )

    def tweak_cloned_fields(self, fields):
        for f in self.clone_ignore_fields:
            fields.pop(f)

        return fields

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context.update({"show_duplicate": True})

        return super().change_view(request, object_id, form_url, extra_context)
