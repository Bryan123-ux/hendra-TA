from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.models import User, Group
from .models import (
    Admin as AdminModel,
    Barang,
    Pelanggan,
    Transaksi,
    DetailTransaksi,
    NotifikasiCRM,
    LaporanCRM,
    LaporanPenjualan,
)
from django.urls import reverse, path
from django.http import HttpResponse
from django.db.models import Sum, Count
from django.db.models.functions import ExtractMonth, ExtractYear
from django.utils.safestring import mark_safe
import calendar
import csv
from reportlab.pdfgen import canvas
from io import BytesIO

# Sembunyikan menu autentikasi default
admin.site.unregister(User)
admin.site.unregister(Group)

admin.site.site_header = "UD. BAROKAH JAYA BETON"
admin.site.site_title = "ADMIN - UD. BAROKAH JAYA BETON"
admin.site.index_title = "Dashboard Admin"

def format_rupiah(value):
    return f"Rp {value:,.0f}".replace(",", ".")

@admin.register(AdminModel)
class AdminAdmin(admin.ModelAdmin):
    list_display = ('username', 'show_password')
    search_fields = ('username',)

    def show_password(self, obj):
        return format_html(
            '<input type="password" value="{}" style="border:none;" readonly>'
            '<button onclick="this.previousElementSibling.type = (this.previousElementSibling.type === \'password\') ? \'text\' : \'password\'">👁</button>',
            obj.password
        )
    show_password.short_description = 'Password'

@admin.register(Barang)
class BarangAdmin(admin.ModelAdmin):
    list_display = ('namaBarang', 'deskripsiBarang', 'foto_barang_kecil', 'harga_rupiah', 'stokBarang', 'action_buttons')
    search_fields = ('namaBarang', 'deskripsiBarang')
    readonly_fields = ('foto_preview',)
    fields = ('namaBarang', 'deskripsiBarang', 'hargaBarang', 'stokBarang', 'fotoBarang', 'foto_preview')
    list_per_page = 5

    def foto_barang_kecil(self, obj):
        if obj.fotoBarang:
            return format_html('<a href="{}" target="_blank"><img src="{}" width="30" height="30" /></a>', obj.fotoBarang.url, obj.fotoBarang.url)
        return '-'

    def foto_preview(self, obj):
        if obj.fotoBarang:
            return format_html('<img src="{}" style="max-width:300px;" />', obj.fotoBarang.url)
        return '-'

    def harga_rupiah(self, obj):
        return format_rupiah(obj.hargaBarang)

    def action_buttons(self, obj):
        edit_url = reverse('admin:penjualan_barang_change', args=[obj.pk])
        delete_url = reverse('admin:penjualan_barang_delete', args=[obj.pk])
        return format_html('<a class="button" href="{}">✏️</a>&nbsp;<a class="button" href="{}">🗑️</a>', edit_url, delete_url)
    action_buttons.short_description = 'Aksi'

@admin.register(Pelanggan)
class PelangganAdmin(admin.ModelAdmin):
    list_display = ('namaPelanggan', 'alamat', 'tanggalLahir', 'noHp', 'pekerjaan', 'username', 'is_loyal', 'ulang_tahun_hari_ini')

    def is_loyal(self, obj):
        return obj.is_loyal()
    is_loyal.boolean = True

    def ulang_tahun_hari_ini(self, obj):
        return obj.is_ulang_tahun_hari_ini()
    ulang_tahun_hari_ini.boolean = True

@admin.register(Transaksi)
class TransaksiAdmin(admin.ModelAdmin):
    list_display = ('idTransaksi', 'tanggal', 'pelanggan', 'total_rupiah', 'statusTransaksi', 'bukti_bayar_thumbnail', 'ulasan', 'action_buttons')
    readonly_fields = ('bukti_bayar_preview',)

    def total_rupiah(self, obj):
        return format_rupiah(obj.total)

    def bukti_bayar_thumbnail(self, obj):
        if obj.buktiBayar:
            return format_html('<a href="{}" target="_blank"><img src="{}" width="30" height="30" /></a>', obj.buktiBayar.url, obj.buktiBayar.url)
        return '-'

    def bukti_bayar_preview(self, obj):
        if obj.buktiBayar:
            return format_html('<img src="{}" style="max-width:300px;" />', obj.buktiBayar.url)
        return '-'

    def action_buttons(self, obj):
        edit_url = reverse('admin:penjualan_transaksi_change', args=[obj.pk])
        delete_url = reverse('admin:penjualan_transaksi_delete', args=[obj.pk])
        return format_html('<a class="button" href="{}">✏️</a>&nbsp;<a class="button" href="{}">🗑️</a>', edit_url, delete_url)
    action_buttons.short_description = 'Aksi'

@admin.register(DetailTransaksi)
class DetailTransaksiAdmin(admin.ModelAdmin):
    list_display = ('transaksi', 'barang', 'jumlahBarang', 'diskon_rupiah', 'subtotal_rupiah', 'action_buttons')
    readonly_fields = ('subtotal',)

    def diskon_rupiah(self, obj):
        return format_rupiah(obj.diskon) if obj.diskon else '-'

    def subtotal_rupiah(self, obj):
        return format_rupiah(obj.subtotal)

    def action_buttons(self, obj):
        edit_url = reverse('admin:penjualan_detailtransaksi_change', args=[obj.pk])
        delete_url = reverse('admin:penjualan_detailtransaksi_delete', args=[obj.pk])
        return format_html('<a class="button" href="{}">✏️</a>&nbsp;<a class="button" href="{}">🗑️</a>', edit_url, delete_url)
    action_buttons.short_description = 'Aksi'

@admin.register(NotifikasiCRM)
class NotifikasiCRMAdmin(admin.ModelAdmin):
    list_display = ('namaPelanggan', 'noHp', 'is_loyal_display', 'ulang_tahun_display', 'produk_terakhir', 'action_buttons')
    search_fields = ('namaPelanggan', 'noHp')

    def is_loyal_display(self, obj):
        return '✅ Loyal' if obj.is_loyal() else '❌'
    is_loyal_display.short_description = 'Loyal'

    def ulang_tahun_display(self, obj):
        return '🎂 Ya' if obj.is_ulang_tahun_hari_ini() else 'Tidak'
    ulang_tahun_display.short_description = 'Ulang Tahun'

    def produk_terakhir(self, obj):
        barang_list = obj.produk_yang_pernah_dibeli()
        if barang_list:
            return format_html("<br>".join([f"• {b.namaBarang}" for b in barang_list]))
        return '-'
    produk_terakhir.short_description = "Produk Pernah Dibeli"

    def action_buttons(self, obj):
        edit_url = reverse('admin:penjualan_pelanggan_change', args=[obj.pk])
        delete_url = reverse('admin:penjualan_pelanggan_delete', args=[obj.pk])
        return format_html('<a class="button" href="{}">✏️</a>&nbsp;<a class="button" href="{}">🗑️</a>', edit_url, delete_url)
    action_buttons.short_description = 'Aksi'

@admin.register(LaporanPenjualan)
class LaporanPenjualanAdmin(admin.ModelAdmin):
    list_display = ('tanggal', 'produk', 'pelanggan', 'jumlah', 'subtotal_rupiah')
    list_filter = ('transaksi__tanggal',)
    actions = ['export_as_pdf', 'export_as_excel']
    search_fields = ('transaksi__pelanggan__namaPelanggan', 'barang__namaBarang')

    def get_queryset(self, request):
        return super().get_queryset(request).filter(transaksi__statusTransaksi='SELESAI')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def tanggal(self, obj):
        return obj.transaksi.tanggal
    tanggal.short_description = "Tanggal"

    def produk(self, obj):
        return obj.barang.namaBarang
    produk.short_description = "Produk"

    def pelanggan(self, obj):
        return obj.transaksi.pelanggan.namaPelanggan
    pelanggan.short_description = "Pelanggan"

    def jumlah(self, obj):
        return obj.jumlahBarang

    def subtotal_rupiah(self, obj):
        return format_rupiah(obj.subtotal)
    subtotal_rupiah.short_description = "Subtotal"

    def export_as_excel(self, request, queryset):
        import csv
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="laporan_penjualan.csv"'

        writer = csv.writer(response)
        writer.writerow(['Tanggal', 'Produk', 'Pelanggan', 'Jumlah', 'Subtotal'])

        for obj in queryset:
            writer.writerow([
                obj.transaksi.tanggal,
                obj.barang.namaBarang,
                obj.transaksi.pelanggan.namaPelanggan,
                obj.jumlahBarang,
                obj.subtotal,
            ])
        return response
    export_as_excel.short_description = "Export ke Excel (CSV)"

    def export_as_pdf(self, request, queryset):
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.enums import TA_CENTER
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []

        styles = getSampleStyleSheet()
        style_title = styles['Heading1']
        style_title.alignment = TA_CENTER
        style_title.fontSize = 16

        title = Paragraph("Laporan Penjualan - UD. BAROKAH JAYA BETON", style_title)
        elements.append(title)
        elements.append(Spacer(1, 12))

        data = [['Tanggal', 'Produk', 'Pelanggan', 'Jumlah', 'Subtotal']]
        for obj in queryset:
            data.append([
                str(obj.transaksi.tanggal),
                obj.barang.namaBarang,
                obj.transaksi.pelanggan.namaPelanggan,
                str(obj.jumlahBarang),
                format_rupiah(obj.subtotal)
            ])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (3, 1), (4, -1), 'RIGHT'),
        ]))

        elements.append(table)

        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="laporan_penjualan.pdf"'
        response.write(pdf)
        return response
    export_as_pdf.short_description = "Export ke PDF"
