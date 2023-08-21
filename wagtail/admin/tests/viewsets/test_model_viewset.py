import datetime

from django.contrib.admin.utils import quote
from django.test import TestCase
from django.urls import reverse

from wagtail.test.testapp.models import FeatureCompleteToy, JSONStreamModel
from wagtail.test.utils.wagtail_tests import WagtailTestUtils


class TestModelViewSetGroup(WagtailTestUtils, TestCase):
    def setUp(self):
        self.user = self.login()

    def test_menu_items(self):
        response = self.client.get(reverse("wagtailadmin_home"))
        self.assertEqual(response.status_code, 200)
        # Menu label falls back to the title-cased app label
        self.assertContains(
            response,
            '"name": "tests", "label": "Tests", "icon_name": "folder-open-inverse"',
        )
        # Title-cased from verbose_name_plural
        self.assertContains(response, "Json Stream Models")
        self.assertContains(response, reverse("streammodel:index"))
        self.assertEqual(reverse("streammodel:index"), "/admin/streammodel/")
        # Set on class
        self.assertContains(response, "JSON MinMaxCount StreamModel")
        self.assertContains(response, reverse("minmaxcount_streammodel:index"))
        self.assertEqual(
            reverse("minmaxcount_streammodel:index"),
            "/admin/minmaxcount-streammodel/",
        )
        # Set on instance
        self.assertContains(response, "JSON BlockCounts StreamModel")
        self.assertContains(response, reverse("blockcounts_streammodel:index"))
        self.assertEqual(
            reverse("blockcounts_streammodel:index"),
            "/admin/blockcounts/streammodel/",
        )


class TestTemplateConfiguration(WagtailTestUtils, TestCase):
    def setUp(self):
        self.user = self.login()

    @classmethod
    def setUpTestData(cls):
        cls.default = JSONStreamModel.objects.create(
            body='[{"type": "text", "value": "foo"}]',
        )
        cls.custom = FeatureCompleteToy.objects.create(name="Test Toy")

    def get_default_url(self, view_name, args=()):
        return reverse(f"streammodel:{view_name}", args=args)

    def get_custom_url(self, view_name, args=()):
        return reverse(f"feature_complete_toy:{view_name}", args=args)

    def test_default_templates(self):
        pk = quote(self.default.pk)
        cases = {
            "index": (
                [],
                "wagtailadmin/generic/index.html",
            ),
            "index_results": (
                [],
                "wagtailadmin/generic/listing_results.html",
            ),
            "add": (
                [],
                "wagtailadmin/generic/create.html",
            ),
            "edit": (
                [pk],
                "wagtailadmin/generic/edit.html",
            ),
            "delete": (
                [pk],
                "wagtailadmin/generic/confirm_delete.html",
            ),
        }
        for view_name, (args, template_name) in cases.items():
            with self.subTest(view_name=view_name):
                response = self.client.get(self.get_default_url(view_name, args=args))
                self.assertTemplateUsed(response, template_name)

    def test_custom_template_lookups(self):
        pk = quote(self.custom.pk)
        cases = {
            "override with index_template_name": (
                "index",
                [],
                "tests/fctoy_index.html",
            ),
            "with app label and model name": (
                "add",
                [],
                "customprefix/tests/featurecompletetoy/create.html",
            ),
            "with app label": (
                "edit",
                [pk],
                "customprefix/tests/edit.html",
            ),
            "without app label and model name": (
                "delete",
                [pk],
                "customprefix/confirm_delete.html",
            ),
        }
        for case, (view_name, args, template_name) in cases.items():
            with self.subTest(case=case):
                response = self.client.get(self.get_custom_url(view_name, args=args))
                self.assertTemplateUsed(response, template_name)
                self.assertContains(
                    response, "<p>Some extra custom content</p>", html=True
                )


class TestCustomColumns(WagtailTestUtils, TestCase):
    def setUp(self):
        self.user = self.login()

    @classmethod
    def setUpTestData(cls):
        FeatureCompleteToy.objects.create(name="Racecar")
        FeatureCompleteToy.objects.create(name="level")
        FeatureCompleteToy.objects.create(name="Lotso")

    def test_list_display(self):
        index_url = reverse("feature_complete_toy:index")
        response = self.client.get(index_url)
        # "name" column
        self.assertContains(response, "Racecar")
        self.assertContains(response, "level")
        self.assertContains(response, "Lotso")
        # BooleanColumn("is_cool")
        soup = self.get_soup(response.content)

        help = soup.select_one("td:has(svg.icon-help)")
        self.assertIsNotNone(help)
        self.assertEqual(help.text.strip(), "None")

        success = soup.select_one("td:has(svg.icon-success.w-text-positive-100)")
        self.assertIsNotNone(success)
        self.assertEqual(success.text.strip(), "True")

        error = soup.select_one("td:has(svg.icon-error.w-text-critical-100)")
        self.assertIsNotNone(error)
        self.assertEqual(error.text.strip(), "False")

        updated_at = soup.select("th a")[-1]
        self.assertEqual(updated_at.text.strip(), "Updated")
        self.assertEqual(updated_at["href"], f"{index_url}?ordering=_updated_at")


class TestListFilter(WagtailTestUtils, TestCase):
    def setUp(self):
        self.user = self.login()

    def get(self, params=None):
        return self.client.get(reverse("feature_complete_toy:index"), params)

    @classmethod
    def setUpTestData(cls):
        FeatureCompleteToy.objects.create(
            name="Buzz Lightyear",
            release_date=datetime.date(1995, 11, 19),
        )
        FeatureCompleteToy.objects.create(
            name="Forky",
            release_date=datetime.date(2019, 6, 11),
        )

    def test_unfiltered_no_results(self):
        FeatureCompleteToy.objects.all().delete()
        response = self.get()
        self.assertContains(response, "There are no feature complete toys to display")
        self.assertContains(
            response,
            '<label class="w-field__label" for="id_release_date" id="id_release_date-label">Release date</label>',
            html=True,
        )
        self.assertContains(
            response,
            '<input type="text" name="release_date" autocomplete="off" id="id_release_date">',
            html=True,
        )
        self.assertTemplateUsed(response, "wagtailadmin/shared/filters.html")

    def test_unfiltered_with_results(self):
        response = self.get()
        self.assertTemplateUsed(response, "wagtailadmin/shared/filters.html")
        self.assertContains(response, "Buzz Lightyear")
        self.assertContains(response, "Forky")
        self.assertNotContains(response, "There are 2 matches")
        self.assertContains(
            response,
            '<label class="w-field__label" for="id_release_date" id="id_release_date-label">Release date</label>',
            html=True,
        )
        self.assertContains(
            response,
            '<input type="text" name="release_date" autocomplete="off" id="id_release_date">',
            html=True,
        )

    def test_empty_filter_with_results(self):
        response = self.get({"release_date": ""})
        self.assertTemplateUsed(response, "wagtailadmin/shared/filters.html")
        self.assertContains(response, "Buzz Lightyear")
        self.assertContains(response, "Forky")
        self.assertNotContains(response, "There are 2 matches")
        self.assertContains(
            response,
            '<label class="w-field__label" for="id_release_date" id="id_release_date-label">Release date</label>',
            html=True,
        )
        self.assertContains(
            response,
            '<input type="text" name="release_date" value="" autocomplete="off" id="id_release_date">',
            html=True,
        )

    def test_filtered_no_results(self):
        response = self.get({"release_date": "1970-01-01"})
        self.assertTemplateUsed(response, "wagtailadmin/shared/filters.html")
        self.assertContains(
            response,
            "No feature complete toys match your query",
        )
        self.assertContains(
            response,
            '<label class="w-field__label" for="id_release_date" id="id_release_date-label">Release date</label>',
            html=True,
        )
        self.assertContains(
            response,
            '<input type="text" name="release_date" value="1970-01-01" autocomplete="off" id="id_release_date">',
            html=True,
        )

    def test_filtered_with_results(self):
        response = self.get({"release_date": "1995-11-19"})
        self.assertTemplateUsed(response, "wagtailadmin/shared/filters.html")
        self.assertContains(response, "Buzz Lightyear")
        self.assertContains(response, "There is 1 match")
        self.assertContains(
            response,
            '<label class="w-field__label" for="id_release_date" id="id_release_date-label">Release date</label>',
            html=True,
        )
        self.assertContains(
            response,
            '<input type="text" name="release_date" value="1995-11-19" autocomplete="off" id="id_release_date">',
            html=True,
        )