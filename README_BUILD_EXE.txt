PANDUAN BUILD EXE - HomePass Group Tool
======================================

Isi paket:
1. AK47_HOME_PASS_GROUP_TOOL_EXE_READY.py
   - Source Python yang sudah dynamic size dan sudah dipasang icon aplikasi.

2. LOGO_APLIKASI_ALL_SIZE.ico
   - Icon aplikasi format .ico multi-size: 16, 20, 24, 32, 40, 48, 64, 128, 256 px.
   - Dipakai untuk icon EXE, taskbar, dan title bar.

3. BUILD_EXE_ONEFILE_WITH_ICON.bat
   - Build utama. Hasil akhirnya satu file EXE.

4. BUILD_EXE_ALTERNATIVE_DIRECT_COMMAND.bat
   - Build alternatif tanpa file spec.

5. RUN_SOURCE_BEFORE_BUILD.bat
   - Untuk tes source Python sebelum dibuat EXE.

Cara pakai di Windows:
1. Extract ZIP ini ke satu folder.
2. Jalankan dulu RUN_SOURCE_BEFORE_BUILD.bat.
3. Jika aplikasi sudah terbuka normal, jalankan BUILD_EXE_ONEFILE_WITH_ICON.bat.
4. Setelah selesai, ambil EXE di folder:
   dist\HomePass Group Tool.exe

Catatan:
- Build EXE Windows sebaiknya dilakukan langsung di Windows.
- Jika dependency gagal terinstall, klik kanan file .bat lalu pilih Run as administrator.
- Jika EXE diblok antivirus, itu umum untuk hasil PyInstaller onefile. Solusi lebih aman adalah build mode onedir atau whitelist folder build.
