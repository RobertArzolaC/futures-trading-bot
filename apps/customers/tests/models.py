from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone

import apps.customers.models
from apps.core import choices
from apps.customers import factories, models
from apps.customers.factories import (
    AccountFactory,
    DirectOrderFactory,
    MedicalTestFactory,
    MedicalTestResultFactory,
    OrderFactory,
    OrderResultFactory,
    PanelFactory,
    PanelTestFactory,
    PatientFactory,
    RangeFactory,
)
from apps.laboratory import choices as laboratory_choices
from apps.laboratory import models as laboratory_models


class TestAccountModel(TestCase):
    def setUp(self):
        """Set up test data."""
        self.organization_account = factories.AccountFactory(is_organization=True)
        self.regular_account = factories.AccountFactory(is_organization=False)
        self.child_account = factories.AccountFactory(
            is_organization=False, parent_account=self.organization_account
        )

    def test_account_creation(self):
        """Test basic account creation."""
        self.assertIsInstance(self.regular_account, apps.customers.models.Account)
        self.assertFalse(self.regular_account.is_organization)
        self.assertIsNone(self.regular_account.parent_account)

    def test_organization_account_creation(self):
        """Test organization account creation."""
        self.assertTrue(self.organization_account.is_organization)
        self.assertIsNone(self.organization_account.parent_account)

    def test_child_account_creation(self):
        """Test child account creation."""
        self.assertFalse(self.child_account.is_organization)
        self.assertEqual(self.child_account.parent_account, self.organization_account)

    def test_prevent_organization_with_parent(self):
        """Test organization account cannot have parent."""
        with self.assertRaises(ValidationError):
            org_account = factories.AccountFactory(
                is_organization=True, parent_account=self.organization_account
            )
            org_account.clean()

    def test_prevent_non_organization_parent(self):
        """Test parent must be organization account."""
        with self.assertRaises(ValidationError):
            child_account = factories.AccountFactory(parent_account=self.regular_account)
            child_account.clean()

    def test_prevent_deep_hierarchy(self):
        """Test only one level of hierarchy is allowed."""
        with self.assertRaises(ValidationError):
            deep_child = factories.AccountFactory(parent_account=self.child_account)
            deep_child.clean()

    def test_str_representation(self):
        """Test string representation."""
        account_with_company = factories.AccountFactory(company_name="Test Company")
        self.assertEqual(str(account_with_company), "Test Company")
        self.assertEqual(
            str(self.regular_account), self.regular_account.user.get_full_name()
        )

    def test_child_accounts_count_property(self):
        """Test child_accounts_count property."""
        factories.AccountFactory(parent_account=self.organization_account)
        factories.AccountFactory(parent_account=self.organization_account)
        self.assertEqual(
            self.organization_account.child_accounts_count, 3
        )  # Including previously created child_account

    def test_full_name_property(self):
        """Test full_name property."""
        self.assertEqual(
            self.regular_account.full_name,
            self.regular_account.user.get_full_name(),
        )

    def test_is_child_account_property(self):
        """Test is_child_account property."""
        self.assertTrue(self.child_account.is_child_account)
        self.assertFalse(self.regular_account.is_child_account)

    def test_get_organization_method(self):
        """Test get_organization method."""
        self.assertEqual(
            self.organization_account.get_organization(),
            self.organization_account,
        )
        self.assertEqual(self.child_account.get_organization(), self.organization_account)
        self.assertIsNone(self.regular_account.get_organization())

    def test_prevent_self_parent(self):
        """Test account cannot be its own parent."""
        account = factories.AccountFactory()
        account.parent_account = account

        with self.assertRaises(IntegrityError) as context:
            account.save()

        # Check that the error message mentions the constraint name
        self.assertIn("prevent_self_parent", str(context.exception))

    def test_patients_count_property(self):
        """Test patients_count property including child accounts."""
        # Create some patients for organization
        for _ in range(3):
            factories.PatientFactory(account=self.organization_account)

        # Create patients for child account
        for _ in range(2):
            factories.PatientFactory(account=self.child_account)

        self.assertEqual(self.organization_account.patients_count, 5)
        self.assertEqual(self.child_account.patients_count, 2)

    def test_medical_tests_count_property(self):
        """Test medical_tests_count property including child accounts."""
        # Create medical tests for organization
        for _ in range(2):
            factories.MedicalTestFactory(account=self.organization_account)

        # Create medical tests for child account
        for _ in range(3):
            factories.MedicalTestFactory(account=self.child_account)

        self.assertEqual(self.organization_account.medical_tests_count, 5)
        self.assertEqual(self.child_account.medical_tests_count, 3)


class PanelModelTest(TestCase):
    def setUp(self):
        self.account = factories.AccountFactory()
        self.test1 = factories.MedicalTestFactory(account=self.account)
        self.test2 = factories.MedicalTestFactory(account=self.account)

        # Create an empty panel
        self.empty_panel = factories.PanelFactory(account=self.account)

        # Create a panel with tests
        self.panel_with_tests = factories.PanelFactory(account=self.account)
        self.panel_with_tests.medical_tests.add(self.test1, self.test2)

        # Create a patient for the account
        self.patient = self.account.patients.create(
            first_name="Test", last_name="Patient"
        )

    def test_panel_creation(self):
        """Test that panels are created correctly"""
        self.assertIsNotNone(self.empty_panel.id)
        self.assertEqual(self.empty_panel.account, self.account)
        self.assertTrue(len(self.empty_panel.title) > 0)
        self.assertTrue(len(self.empty_panel.description) > 0)

    def test_panel_string_representation(self):
        """Test the string representation of the panel"""
        self.assertEqual(str(self.empty_panel), self.empty_panel.title)

    def test_panel_with_tests(self):
        """Test the relationship between panel and medical tests"""
        self.assertEqual(self.panel_with_tests.medical_tests.count(), 2)
        self.assertIn(self.test1, self.panel_with_tests.medical_tests.all())
        self.assertIn(self.test2, self.panel_with_tests.medical_tests.all())

    def test_formatted_data_property(self):
        """Test the formatted_data property of the panel"""
        formatted_data = self.panel_with_tests.formatted_data

        self.assertEqual(formatted_data["id"], self.panel_with_tests.id)
        self.assertEqual(formatted_data["title"], self.panel_with_tests.title)
        self.assertEqual(formatted_data["description"], self.panel_with_tests.description)
        self.assertEqual(formatted_data["medical_tests_count"], 2)
        self.assertEqual(len(formatted_data["patients_ids"]), 1)
        self.assertIn(self.patient.id, formatted_data["patients_ids"])

    def test_get_panels_by_user(self):
        """Test the class method get_panels_by_user"""
        user = self.account.user
        panels = laboratory_models.Panel.get_panels_by_user(user)

        self.assertIn(self.empty_panel, panels)
        self.assertIn(self.panel_with_tests, panels)

    def test_get_panels_info_by_patient(self):
        """Test the class method get_panels_info_by_patient"""
        user = self.account.user
        panel_info = laboratory_models.Panel.get_panels_info_by_patient(
            user, self.patient
        )

        self.assertEqual(len(panel_info), 2)  # There should be 2 panels

        # Verify that the first panel has the correctly formatted data
        panel_data = next(
            info for info in panel_info if info["id"] == self.panel_with_tests.id
        )
        self.assertEqual(panel_data["medical_tests_count"], 2)
        self.assertEqual(len(panel_data["patients_ids"]), 1)


class PanelTestModelTest(TestCase):
    def setUp(self):
        self.panel = PanelFactory()
        self.medical_test = MedicalTestFactory()
        self.panel_test = PanelTestFactory(
            panel=self.panel, medical_test=self.medical_test, order=1
        )

    def test_panel_test_creation(self):
        """Test that panel tests are created correctly"""
        self.assertIsNotNone(self.panel_test.id)
        self.assertEqual(self.panel_test.panel, self.panel)
        self.assertEqual(self.panel_test.medical_test, self.medical_test)
        self.assertEqual(self.panel_test.order, 1)

    def test_panel_test_string_representation(self):
        """Test the string representation of panel test"""
        expected = f"{self.panel.title} - {self.medical_test.title}"
        self.assertEqual(str(self.panel_test), expected)

    def test_unique_panel_test_constraint(self):
        """Test that a panel cannot have the same test twice"""
        with self.assertRaises(Exception):  # Should raise a unique constraint error
            PanelTestFactory(panel=self.panel, medical_test=self.medical_test, order=2)

    def test_panel_tests_ordering(self):
        """Test that panel tests are ordered correctly"""
        another_test = MedicalTestFactory()
        another_panel_test = PanelTestFactory(
            panel=self.panel, medical_test=another_test, order=2
        )

        # Get all panel tests for the panel ordered by order
        panel_tests = models.PanelTest.objects.filter(panel=self.panel).order_by("order")

        self.assertEqual(panel_tests[0], self.panel_test)
        self.assertEqual(panel_tests[1], another_panel_test)


class RangeModelTest(TestCase):
    def setUp(self):
        self.medical_test = MedicalTestFactory(
            has_age_range=True, has_gender_range=True, has_period_range=True
        )
        self.range = RangeFactory(
            medical_test=self.medical_test,
            min_normal_value=Decimal("3.5"),
            max_normal_value=Decimal("7.5"),
            min_optimal_value=Decimal("4.0"),
            max_optimal_value=Decimal("6.0"),
            min_red_line_value=Decimal("2.0"),
            max_red_line_value=Decimal("9.0"),
            min_age=20,
            max_age=50,
            gender=choices.GenderChoices.MALE,
            menstrual_period=laboratory_choices.MenstrualPeriodChoices.NOT_APPLICABLE,
        )

    def test_range_creation(self):
        """Test that ranges are created correctly"""
        self.assertIsNotNone(self.range.id)
        self.assertEqual(self.range.medical_test, self.medical_test)
        self.assertEqual(self.range.min_normal_value, Decimal("3.5"))
        self.assertEqual(self.range.max_normal_value, Decimal("7.5"))
        self.assertEqual(self.range.min_optimal_value, Decimal("4.0"))
        self.assertEqual(self.range.max_optimal_value, Decimal("6.0"))
        self.assertEqual(self.range.min_age, 20)
        self.assertEqual(self.range.max_age, 50)
        self.assertEqual(self.range.gender, choices.GenderChoices.MALE)

    def test_range_string_representation(self):
        """Test the string representation of range"""
        self.assertEqual(str(self.range), self.medical_test.title)

    def test_multiple_ranges_for_test(self):
        """Test that a medical test can have multiple ranges"""
        female_range = RangeFactory(
            medical_test=self.medical_test,
            min_normal_value=Decimal("2.5"),
            max_normal_value=Decimal("6.5"),
            gender=choices.GenderChoices.FEMALE,
        )

        ranges = models.Range.objects.filter(medical_test=self.medical_test)
        self.assertEqual(ranges.count(), 2)
        self.assertIn(self.range, ranges)
        self.assertIn(female_range, ranges)


class OrderModelTest(TestCase):
    def setUp(self):
        self.account = AccountFactory()
        self.patient = PatientFactory(account=self.account)
        self.panel1 = PanelFactory(account=self.account)
        self.panel2 = PanelFactory(account=self.account)

        self.test1 = MedicalTestFactory(account=self.account)
        self.test2 = MedicalTestFactory(account=self.account)

        # Add tests to panels
        self.panel1.medical_tests.add(self.test1, self.test2)
        self.panel2.medical_tests.add(self.test1)

        # Create order with panels
        self.order = OrderFactory(
            patient=self.patient,
            status=laboratory_choices.OrderStatusChoices.PENDING,
            external_id="ORD-123456",
            collected_at=timezone.now(),
            received_at=timezone.now(),
        )
        self.order.panels.add(self.panel1, self.panel2)

    def test_order_creation(self):
        """Test that orders are created correctly"""
        self.assertIsNotNone(self.order.id)
        self.assertEqual(self.order.patient, self.patient)
        self.assertEqual(self.order.status, laboratory_choices.OrderStatusChoices.PENDING)
        self.assertEqual(self.order.external_id, "ORD-123456")
        self.assertIsNotNone(self.order.collected_at)
        self.assertIsNotNone(self.order.received_at)

    def test_order_string_representation(self):
        """Test the string representation of order"""
        self.assertEqual(str(self.order), self.order.external_id)

    def test_order_panels_relationship(self):
        """Test the relationship between order and panels"""
        self.assertEqual(self.order.panels.count(), 2)
        self.assertIn(self.panel1, self.order.panels.all())
        self.assertIn(self.panel2, self.order.panels.all())

    def test_get_panels_with_tests(self):
        """Test get_panels_with_tests method"""
        panels_with_tests = self.order.get_panels_with_tests()

        self.assertEqual(len(panels_with_tests), 2)
        self.assertIn(self.panel1, panels_with_tests)
        self.assertIn(self.panel2, panels_with_tests)

        # Check tests in panels
        self.assertEqual(len(list(panels_with_tests[self.panel1])), 2)
        self.assertEqual(len(list(panels_with_tests[self.panel2])), 1)

    def test_get_total_tests(self):
        """Test get_total_tests method"""
        total_tests = self.order.get_total_tests()
        # Note: test1 appears in both panels but should be counted twice
        self.assertEqual(total_tests, 3)

    def test_get_time_since_created(self):
        """Test get_time_since_created method"""
        time_since = self.order.get_time_since_created()
        self.assertTrue(isinstance(time_since, str))
        self.assertTrue("minutes ago" in time_since or "seconds ago" in time_since)


class OrderResultModelTest(TestCase):
    def setUp(self):
        self.account = AccountFactory()
        self.patient = PatientFactory(account=self.account)
        self.panel = PanelFactory(account=self.account)

        self.test1 = MedicalTestFactory(account=self.account)
        self.test2 = MedicalTestFactory(account=self.account)

        # Add tests to panel
        self.panel.medical_tests.add(self.test1, self.test2)

        # Create order with panel
        self.order = OrderFactory(
            patient=self.patient,
            status=laboratory_choices.OrderStatusChoices.PENDING,
        )
        self.order.panels.add(self.panel)

        # Create order result
        self.order_result = OrderResultFactory(
            order=self.order,
            status=laboratory_choices.OrderStatusChoices.PENDING,
            processed_at=timezone.now(),
        )

    def test_order_result_creation(self):
        """Test that order results are created correctly"""
        self.assertIsNotNone(self.order_result.id)
        self.assertEqual(self.order_result.order, self.order)
        self.assertEqual(
            self.order_result.status,
            laboratory_choices.OrderStatusChoices.PENDING,
        )
        self.assertIsNotNone(self.order_result.processed_at)

    def test_order_result_string_representation(self):
        """Test the string representation of order result"""
        expected = f"Results for Order: {self.order}"
        self.assertEqual(str(self.order_result), expected)

    def test_update_status_with_no_results(self):
        """Test update_status method with no test results"""
        self.order_result.update_status()
        self.assertEqual(
            self.order_result.status,
            laboratory_choices.OrderStatusChoices.PENDING,
        )

    def test_update_status_with_completed_results(self):
        """Test update_status method with all results completed"""
        # Create test results that are all completed
        MedicalTestResultFactory(
            order_result=self.order_result,
            medical_test=self.test1,
            panel=self.panel,
            value=Decimal("5.123"),  # Ensure value has fewer than 10 digits in total
            status=laboratory_choices.OrderStatusChoices.COMPLETED,
        )
        MedicalTestResultFactory(
            order_result=self.order_result,
            medical_test=self.test2,
            panel=self.panel,
            value=Decimal("7.456"),  # Ensure value has fewer than 10 digits in total
            status=laboratory_choices.OrderStatusChoices.COMPLETED,
        )

        self.order_result.update_status()
        self.assertEqual(
            self.order_result.status,
            laboratory_choices.OrderStatusChoices.COMPLETED,
        )
        self.assertIsNotNone(self.order_result.validated_at)

    def test_completion_percentage_property(self):
        """Test completion_percentage property"""
        # Create test results with mixed statuses
        MedicalTestResultFactory(
            order_result=self.order_result,
            medical_test=self.test1,
            panel=self.panel,
            value=Decimal("5.555"),
            status=laboratory_choices.OrderStatusChoices.COMPLETED,
        )
        MedicalTestResultFactory(
            order_result=self.order_result,
            medical_test=self.test2,
            panel=self.panel,
            value=Decimal("6.666"),
            status=laboratory_choices.OrderStatusChoices.PENDING,
        )
        # import ipdb;ipdb.set_trace()
        # TODO: Posible bug o caso borde
        self.assertEqual(self.order_result.completion_percentage, 50.0)

    def test_order_status_sync(self):
        """Test that order status syncs with order result status"""
        self.order_result.status = laboratory_choices.OrderStatusChoices.COMPLETED
        self.order_result.save()

        # Reload order from database
        self.order.refresh_from_db()
        self.assertEqual(
            self.order.status, laboratory_choices.OrderStatusChoices.COMPLETED
        )


class MedicalTestResultModelTest(TestCase):
    def setUp(self):
        self.account = AccountFactory()
        self.patient = PatientFactory(account=self.account)
        self.panel = PanelFactory(account=self.account)

        self.medical_test = MedicalTestFactory(
            account=self.account, has_age_range=True, has_gender_range=True
        )

        self.range = RangeFactory(
            medical_test=self.medical_test,
            min_normal_value=Decimal("3.5"),
            max_normal_value=Decimal("7.5"),
            min_optimal_value=Decimal("4.0"),
            max_optimal_value=Decimal("6.0"),
            min_age=0,
            max_age=100,
            gender=choices.GenderChoices.FEMALE,
        )

        # Add test to panel
        self.panel.medical_tests.add(self.medical_test)

        # Create order with panel
        self.order = OrderFactory(patient=self.patient)
        self.order.panels.add(self.panel)

        # Create order result
        self.order_result = OrderResultFactory(order=self.order)

        # Create test result
        self.test_result = MedicalTestResultFactory(
            order_result=self.order_result,
            medical_test=self.medical_test,
            panel=self.panel,
            value=Decimal("5.0"),
            status=laboratory_choices.OrderStatusChoices.PENDING,
        )

    def test_test_result_creation(self):
        self.assertIsNotNone(self.test_result.id)
        self.assertEqual(self.test_result.order_result, self.order_result)
        self.assertEqual(self.test_result.medical_test, self.medical_test)
        self.assertEqual(self.test_result.panel, self.panel)
        self.assertEqual(self.test_result.value, Decimal("5.0"))
        self.assertEqual(
            self.test_result.status,
            laboratory_choices.OrderStatusChoices.COMPLETED,
        )

    def test_test_result_string_representation(self):
        """Test the string representation of test result"""
        base_str = f"{self.medical_test} - Panel: {self.panel}"
        expected = f"{base_str} - Order: {self.order_result.order}"
        self.assertEqual(str(self.test_result), expected)

    def test_get_appropriate_range(self):
        """Test get_appropriate_range method finds correct range"""
        range_obj = self.test_result.get_appropriate_range(self.patient)
        self.assertEqual(range_obj, self.range)

    def test_evaluate_level_normal(self):
        """Test that evaluate_level correctly identifies normal values"""
        self.test_result.value = Decimal("5.0")  # Within normal and optimal range
        level = self.test_result.evaluate_level(self.range)
        self.assertEqual(level, laboratory_choices.TestResultLevelChoices.OPTIMAL_RANGE)

    def test_evaluate_level_out_of_range(self):
        """Test that evaluate_level correctly identifies out of range values"""
        self.test_result.value = Decimal("8.5")  # Above normal range
        level = self.test_result.evaluate_level(self.range)
        self.assertEqual(level, laboratory_choices.TestResultLevelChoices.OUT_OF_RANGE)

    def test_save_updates_level_and_status(self):
        """Test that saving a result updates its level and status"""
        self.test_result.value = Decimal("3.7")  # Within normal range but not optimal
        self.test_result.save()

        # Result should be marked as completed and level should be set
        self.assertEqual(
            self.test_result.status,
            laboratory_choices.OrderStatusChoices.COMPLETED,
        )
        self.assertEqual(
            self.test_result.level,
            laboratory_choices.TestResultLevelChoices.NORMAL_RANGE,
        )

        # Order result status should be updated
        self.order_result.refresh_from_db()
        self.assertEqual(
            self.order_result.status,
            laboratory_choices.OrderStatusChoices.COMPLETED,
        )

    def test_is_out_of_range_property(self):
        """Test is_out_of_range property"""
        self.test_result.level = laboratory_choices.TestResultLevelChoices.OUT_OF_RANGE
        self.assertTrue(self.test_result.is_out_of_range)

        self.test_result.level = laboratory_choices.TestResultLevelChoices.NORMAL_RANGE
        self.assertFalse(self.test_result.is_out_of_range)

    def test_formatted_data_property(self):
        """Test formatted_data property"""
        formatted_data = self.test_result.formatted_data

        self.assertEqual(formatted_data["id"], self.test_result.id)
        self.assertEqual(formatted_data["order_id"], self.order.id)
        self.assertEqual(formatted_data["panel_id"], self.panel.id)
        self.assertEqual(formatted_data["panel_name"], self.panel.title)
        self.assertEqual(formatted_data["test_name"], self.medical_test.title)
        self.assertEqual(formatted_data["value"], float(self.test_result.value))


class DirectOrderModelTest(TestCase):
    def setUp(self):
        self.direct_order = DirectOrderFactory(
            specimen_id="SPEC-123456",
            status=laboratory_choices.OrderStatusChoices.PENDING,
        )

    def test_direct_order_creation(self):
        """Test that direct orders are created correctly"""
        self.assertIsNotNone(self.direct_order.id)
        self.assertEqual(self.direct_order.specimen_id, "SPEC-123456")
        self.assertEqual(
            self.direct_order.status,
            laboratory_choices.OrderStatusChoices.PENDING,
        )
        self.assertIsNone(self.direct_order.csv_file.name)
        self.assertIsNone(self.direct_order.pdf_file.name)

    def test_direct_order_string_representation(self):
        """Test the string representation of direct order"""
        self.assertEqual(str(self.direct_order), self.direct_order.specimen_id)

    def test_unique_specimen_id_constraint(self):
        """Test that specimen_id must be unique"""
        with self.assertRaises(Exception):  # Should raise a unique constraint error
            DirectOrderFactory(specimen_id="SPEC-123456")
