from django.db import models
import os
from uuid import uuid4

# Fungsi untuk upload bukti bayar
def upload_bukti_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid4().hex}.{ext}"
    return os.path.join('bukti_bayar', filename)

class Admin(models.Model):
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=50)

    def __str__(self):
        return self.username

class Barang(models.Model):
    namaBarang = models.CharField(max_length=100)
    deskripsiBarang = models.TextField()
    hargaBarang = models.DecimalField(max_digits=12, decimal_places=0)
    stokBarang = models.IntegerField()
    fotoBarang = models.ImageField(upload_to='foto_barang/', blank=True, null=True)

    def __str__(self):
        return self.namaBarang

class Pelanggan(models.Model):
    namaPelanggan = models.CharField(max_length=100)
    alamat = models.TextField()
    tanggalLahir = models.DateField()
    noHp = models.CharField(max_length=15)
    pekerjaan = models.CharField(max_length=50)
    username = models.CharField(max_length=50)

    def __str__(self):
        return self.namaPelanggan

    def is_ulang_tahun_hari_ini(self):
        from datetime import date
        today = date.today()
        return self.tanggalLahir.month == today.month and self.tanggalLahir.day == today.day

    def total_transaksi_selesai(self):
        return self.transaksi_set.filter(statusTransaksi='SELESAI').count()

    def is_loyal(self):
        return self.total_transaksi_selesai() >= 3

    def produk_yang_pernah_dibeli(self):
        from django.db.models import Prefetch
        transaksi_selesai = self.transaksi_set.filter(statusTransaksi='SELESAI')
        detail = DetailTransaksi.objects.filter(transaksi__in=transaksi_selesai).select_related('barang')
        return list({d.barang for d in detail})

class Transaksi(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SELESAI', 'Selesai'),
        ('BATAL', 'Batal'),
    ]
    idTransaksi = models.AutoField(primary_key=True)
    tanggal = models.DateField()
    total = models.DecimalField(max_digits=12, decimal_places=0)
    statusTransaksi = models.CharField(max_length=10, choices=STATUS_CHOICES)
    buktiBayar = models.ImageField(upload_to=upload_bukti_path, blank=True, null=True)
    ulasan = models.TextField(blank=True, null=True)
    pelanggan = models.ForeignKey(Pelanggan, on_delete=models.CASCADE)

    def __str__(self):
        return f"Transaksi {self.idTransaksi}"

class DetailTransaksi(models.Model):
    transaksi = models.ForeignKey(Transaksi, on_delete=models.CASCADE)
    barang = models.ForeignKey(Barang, on_delete=models.CASCADE)
    jumlahBarang = models.IntegerField()
    diskon = models.DecimalField(max_digits=12, decimal_places=0, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=0, editable=False)

    def save(self, *args, **kwargs):
        harga_total = self.barang.hargaBarang * self.jumlahBarang
        if self.diskon:
            self.subtotal = max(harga_total - self.diskon, 0)
        else:
            self.subtotal = harga_total
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaksi} - {self.barang}"

# === Proxy Model: Notifikasi CRM ===
class NotifikasiCRM(Pelanggan):
    class Meta:
        proxy = True
        verbose_name = "Notifikasi CRM"
        verbose_name_plural = "Notifikasi CRM"

# === Proxy Model: Laporan CRM ===
class LaporanCRM(models.Model):
    class Meta:
        managed = False
        verbose_name = "Laporan"
        verbose_name_plural = "Laporan"

# === Proxy Model: Laporan Penjualan Detail ===
class LaporanPenjualan(DetailTransaksi):
    class Meta:
        proxy = True
        verbose_name = "Laporan Penjualan"
        verbose_name_plural = "Laporan Penjualan"


