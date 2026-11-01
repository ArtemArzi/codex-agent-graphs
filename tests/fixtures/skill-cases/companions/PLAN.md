# Принятая задача

normalize_label должна убирать только крайние пробелы и приводить буквы к нижнему регистру. Внутренние пробелы сохраняются. Публичный return type: str.

Связи: labels.normalize_label -> service.build_record -> report.export_label. Подтвердить imports по коду. Проверки: `python3 checks.py labels`, затем `python3 checks.py report`. Результаты и неизвестные сохраняются здесь.
