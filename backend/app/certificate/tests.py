# tests/test_integration.py
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.base import ContentFile

from baseuser.models import BaseUser
from certificate.models import Certificate
from courses.models import Course

class CertificateIntegrationTest(TestCase):
    
    def setUp(self):
        self.client = Client()
        self.user = BaseUser.objects.create(
            username="testuser",
            email="test@example.com"
        )
        self.user.set_password("testpass")
        self.user.save()
        self.client.login(username="testuser", password="testpass")
        
        self.course = Course.objects.create(title="Test Course")
        self.cert = Certificate.objects.create(
            user=self.user,
            course=self.course,
            certificate_code="TEST123",
            status='completed'
        )
    
    def test_verify_page(self):
        """Tekshirish sahifasi ishlashi"""
        response = self.client.get(
            reverse('certificates:verify', args=['TEST123'])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Course")
        self.assertContains(response, "testuser")
    
    def test_download_pdf(self):
        """PDF yuklab olish ishlashi"""
        # PDF fayl qo'shish
        self.cert.pdf_file.save('test.pdf', ContentFile(b'PDF content'))
        self.cert.save()
        
        response = self.client.get(
            reverse('certificates:download', args=[str(self.cert.pk)])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
    
    def test_admin_regenerate(self):
        """Admin panelda qayta generatsiya"""
        response = self.client.post(
            reverse('admin:certificates_certificate_regenerate', args=[str(self.cert.pk)])
        )
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_api_verify(self):
        """API orqali tekshirish"""
        response = self.client.get(
            reverse('api:certificate-verify', args=['TEST123'])
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['is_valid'])
        self.assertEqual(data['user'], 'testuser')