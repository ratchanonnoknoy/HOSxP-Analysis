# HOSxP Schema Explorer

เครื่องมือ CLI สำหรับ "แกะ" โครงสร้างตารางฐานข้อมูล HOSxP ในเทอร์มินัล
ใช้ได้เมื่อไม่มี data dictionary: ดู field, type, key, index, comment และค่าตัวอย่างได้ในคำสั่งเดียว

## Overview

Reverse-engineered the HOSxP database schema using SQL `DESCRIBE` / `information_schema` queries,
analyzing 15+ OPD tables and 1M+ patient records without a data dictionary,
saving THB 300,000 in training costs.

## Features

- แสดงโครงสร้างตาราง: ชื่อฟิลด์, ชนิดข้อมูล, Key, Null, Comment
- ไฮไลต์ Primary Key (เหลือง) และคีย์ที่ใช้ join บ่อย เช่น `hn`, `vn`, `an`, `cid` (ม่วง)
- แสดงค่าตัวอย่างของแต่ละฟิลด์ ช่วยเดาความหมายของชื่อย่อ
- แสดง Index และจำนวนแถวโดยประมาณ
- ถ้าพิมพ์ชื่อตารางผิด จะแนะนำตารางที่ชื่อใกล้เคียง
- โหมด `--no-sample` ซ่อนข้อมูลผู้ป่วยเวลาแชร์หน้าจอ

## Requirements

- Python 3.9+
- MySQL / MariaDB ของ HOSxP (สิทธิ์อ่านอย่างเดียวก็พอ)

```bash
pip install pandas sqlalchemy pymysql rich
```

## Configuration

แก้ค่าเชื่อมต่อด้านบนของสคริปต์ หรือใช้ environment variable (แนะนำ):

```bash
export HOS_HOST=127.0.0.1
export HOS_USER=readonly_user
export HOS_PASSWORD=your_password
export HOS_DB=hos
```

> ⚠️ อย่า commit รหัสผ่านจริงลง GitHub และควรใช้ user ที่มีสิทธิ์ `SELECT` เท่านั้น

## Usage

### SQL

1. เปิดไฟล์ `.sql` ของ query ที่ต้องการ
2. แก้ชื่อตารางหรือเงื่อนไข
3. รันใน SQL editor

## Example Output

![terminal](https://res.cloudinary.com/dpa96jvla/image/upload/v1794484631/%E0%B8%AA%E0%B8%81%E0%B8%A3%E0%B8%B5%E0%B8%99%E0%B8%8A%E0%B9%87%E0%B8%AD%E0%B8%95_2026-11-12_185548_z49fl2.png)

## Privacy & Security

- คอลัมน์ Sample ดึงข้อมูลจริง (ชื่อ, เลขบัตรประชาชน ฯลฯ) ห้ามแคปหน้าจอ/แชร์โดยไม่ใช้ `--no-sample`
- ภาพตัวอย่างใน README ต้องเป็นข้อมูลที่ปิดบังแล้ว หรือรันด้วย `--no-sample`
- ห้ามอัปโหลดข้อมูลผู้ป่วยจริงหรือ dump ฐานข้อมูลขึ้น repo สาธารณะ (PDPA)

## Project Structure

```
hosxp/
├── hos_desc.py     # สคริปต์หลัก
├── sql/            # query ที่ใช้บ่อย
├── docs/           # screenshot
└── README.md
```

## License

MIT
