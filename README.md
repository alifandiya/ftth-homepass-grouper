# 🚀 FTTH Homepassed Boundary Grouper (AK-47 Advanced Edition)

![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)
![UI Style](https://img.shields.io/badge/UI-Modern__Flicker__Free-orange)
![Dependency](https://img.shields.io/badge/Dependencies-Zero__External-brightgreen)

**FTTH Homepassed Boundary Grouper** adalah alat otomatisasi geospasial berbasis desktop yang dirancang khusus untuk mempercepat pemrosesan data perencanaan jaringan serat optik (*Fiber to the Home*). Aplikasi ini secara cerdas mengelompokkan ribuan titik koordinat pelanggan (*Homepassed*) ke dalam area poligon distribusi optik (*Boundary FAT*) secara instan.

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/ad7268ad-63c7-4f4d-b17c-b1d1767fbff9" />

---

## ✨ Fitur Unggulan

* **⚡ Performa Tanpa Lag (Zero-Dependency):** Tidak membutuhkan instalasi pustaka berat seperti `geopandas` atau `shapely`. Cukup jalankan langsung menggunakan Python bawaan!
* **🎯 Algoritma Cerdas Dua Tahap:** Menggunakan kombinasi saringan kotak pembatas (*Bounding Box Filter*) dan metode *Ray Casting* untuk memastikan perhitungan spasial berjalan kilat pada puluhan ribu titik.
* **🕳️ Dukungan Inner Boundary (Hole):** Mampu mendeteksi lubang di dalam poligon cakupan sehingga status pengelompokan titik tetap akurat (`HP UNCOVER`).
* **🔄 Asynchronous Multi-Threading:** Antarmuka tetap responsif, dinamis, dan bebas macet (*No Flicker / Not Responding*) saat komputasi berat sedang berlangsung.
* **🌐 Antarmuka Multibahasa (Localization):** Mendukung perpindahan bahasa instan (Bahasa Indonesia & English) langsung dari menu utama.

---

## ⚙️ Cara Kerja Aplikasi

Aplikasi menyederhanakan *workflow* GIS Anda yang rumit ke dalam 3 langkah instan:

1. **Input:** Ekstraksi data KML/KMZ hasil survei lapangan secara otomatis.
2. **Proses:** Filter spasial cepat berbasis koordinat matematika murni.
3. **Output:** Menghasilkan berkas KMZ terstruktur baru yang rapi berdasarkan folder hierarki FDT/FAT tanpa merusak data asli.

---

## 🚀 Cara Menjalankan

Karena aplikasi ini dikembangkan dengan prinsip **Zero-Dependency**, Anda tidak perlu melakukan instalasi pihak ketiga lewat `pip`.

[![Latest Release](https://img.shields.io/github/v/release/alifandiya/ftth-homepass-grouper?logo=github&color=blue)](https://github.com/alifandiya/ftth-homepass-grouper/releases)

---

## 📥 Download Berkas Siap Pakai

Bagi pengguna umum atau tim *planner* lapangan yang ingin langsung menggunakan aplikasi ini, Anda dapat mengunduh versi rilis stabil terbaru secara instan melalui tautan di bawah ini:

➡️ [**Download Latest Release (AK-47 V6 Modern UI)**](https://github.com/alifandiya/ftth-homepass-grouper/releases/latest)

> 💡 **Tip:** Cukup unduh berkas `.exe` dari halaman rilis tersebut.

---

## 👥 Credits & Dynamic Growth
* **Original Blueprint / Initial Draft:** Jepri Septiono
* **Core Spatial Logic & GUI Development:** [Alif Nasrullah]
