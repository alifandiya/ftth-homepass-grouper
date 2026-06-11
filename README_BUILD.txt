PANDUAN BUILD HOMEPASS GROUP TOOL KE EXE
========================================

Isi paket ini:
1. main_launcher.py
   Launcher Python untuk menjalankan GUI dari file .pyd.

2. homepassed_boundary_fat_gui_prototype_v6_modern_ui.pyd
   File module hasil compile Cython. Nama sudah disesuaikan agar bisa di-import Python.

3. HomePass_all_sizes.ico
   Icon aplikasi multi-size: 16, 24, 32, 48, 64, 128, dan 256 px.

4. HomePass_Group_Tool.spec
   Konfigurasi PyInstaller siap pakai, termasuk collect_all customtkinter.

5. BUILD_EXE.bat
   Script otomatis untuk membuat EXE.

6. TEST_RUN_APP.bat
   Script untuk mengetes aplikasi dari source folder sebelum dibuat EXE.

7. requirements_build.txt
   Dependency build.

Cara build di Windows:
1. Pastikan Python 3.14 Windows 64-bit sudah terpasang.
2. Ekstrak ZIP ini ke folder yang path-nya sederhana, contoh:
   C:\HomePass_Build
3. Klik kanan BUILD_EXE.bat, pilih Run as administrator bila diperlukan.
4. Tunggu proses selesai.
5. EXE hasil build ada di:
   dist\HomePass_Group_Tool.exe

Catatan penting:
- File .pyd yang diberikan adalah binary Windows 64-bit CPython 3.14. Build harus dijalankan di Windows 64-bit dengan Python 3.14.
- Jika muncul error import .pyd, biasanya versi Python tidak cocok dengan binary .pyd.
- Dari metadata file Cython, module ini bernama:
  homepassed_boundary_fat_gui_prototype_v6_modern_ui
- Bila ingin ganti nama EXE, ubah nilai APP_NAME di file HomePass_Group_Tool.spec.
- Icon file EXE sudah memakai HomePass_all_sizes.ico.
- Icon window juga dicoba dipasang dari main_launcher.py melalui iconbitmap.
