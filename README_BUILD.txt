PANDUAN BUILD HOMEPASS GROUP TOOL KE .EXE
==========================================

Isi paket:
1. launcher.py
   Entry point untuk menjalankan GUI dari file .pyd.

2. AK47_HOME_PASS_GROUP_TOOL_14INCH_SCROLLFIX.cp314-win_amd64.pyd
   Modul aplikasi hasil compile Cython. File ini hanya cocok untuk Windows 64-bit dengan Python 3.14 64-bit.

3. HomePass_Group_Tool_icon_all_sizes.ico
   Icon aplikasi multi-size: 16, 20, 24, 32, 40, 48, 64, 96, 128, dan 256 px.
   Icon ini dipasang ke .exe dan window aplikasi.

4. HomePass_symbol_only_icon_all_sizes.ico
   Icon alternatif khusus simbol rumah, lebih jelas untuk taskbar kecil.
   Kalau ingin pakai icon ini, ganti nama icon di file HomePass_Group_Tool.spec dan launcher.py.

5. HomePass_Group_Tool.spec
   Konfigurasi PyInstaller untuk build one-file .exe tanpa console.

6. BUILD_EXE.bat
   Script otomatis untuk install dependency dan membuat .exe.

7. TEST_RUN_BEFORE_BUILD.bat
   Tes menjalankan aplikasi sebelum build.

8. CLEAN_BUILD.bat
   Membersihkan folder build/dist/cache.

Langkah build:
1. Ekstrak ZIP ini di Windows.
2. Pastikan Python 3.14 64-bit sudah terpasang.
3. Jalankan TEST_RUN_BEFORE_BUILD.bat dulu.
4. Jika aplikasi sudah bisa terbuka, jalankan BUILD_EXE.bat.
5. Hasil akhir berada di:
   dist\HomePass Group Tool.exe

Catatan penting:
- File .pyd Anda bernama cp314-win_amd64, sehingga tidak bisa dibuild/test memakai Python 3.10, 3.11, 3.12, atau 3.13.
- Jangan rename file .pyd kecuali juga mengubah import di launcher.py.
- Jika aplikasi gagal terbuka setelah build, cek file HomePass_error_log.txt.
- Jika icon taskbar masih menampilkan icon default Windows, coba pin ulang aplikasi atau restart Explorer karena Windows sering menyimpan cache icon.
