CARA BUILD HOMEPASS GROUP TOOL MENJADI EXE
==========================================

Isi paket:
1. AK47_HP_GROUPING_ADVANCED_V6_MODERN_GUI.pyd
   - Module aplikasi hasil compile Cython.
   - Dari pengecekan file, module ini membutuhkan Python 3.14 64-bit / python314.dll.

2. HomePass_all_size.ico
   - Icon multi-size: 16, 20, 24, 32, 40, 48, 64, 72, 96, 128, 256 px.
   - Dipakai sebagai icon EXE dan icon window aplikasi.

3. run_homepass.py
   - Launcher kecil agar file .pyd bisa dijalankan sebagai aplikasi.

4. AK47_HomePass.spec
   - Konfigurasi PyInstaller onefile/windowed.

5. BUILD_HOMEPASS_EXE.bat
   - Klik kanan > Run as administrator, atau double click.
   - Output EXE akan muncul di folder: dist\HomePass_Group_Tool.exe

6. RUN_TEST_BEFORE_BUILD.bat
   - Opsional untuk tes apakah aplikasi bisa dibuka sebelum dibuat EXE.

LANGKAH BUILD
=============
1. Install Python 3.14 64-bit.
2. Buka folder ini di Windows.
3. Jalankan RUN_TEST_BEFORE_BUILD.bat untuk tes awal.
4. Jalankan BUILD_HOMEPASS_EXE.bat.
5. Ambil file hasil build:
   dist\HomePass_Group_Tool.exe

CATATAN PENTING
===============
- Jangan build memakai Python 3.12/3.13 karena file .pyd yang diberikan membutuhkan python314.dll.
- Jika ingin memakai Python versi lain, file .pyd harus di-compile ulang dari source Python/Cython sesuai versi Python tersebut.
- Build ini menggunakan mode --windowed/console=False, jadi aplikasi GUI tidak membuka jendela CMD.
