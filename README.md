# ML в механике — журнал выполнения задания

Репозиторий курса: [st115592/ML_task_zero](https://github.com/st115592/ML_task_zero). Исследуемый проект — [AakaashfromIndia/OrbitalMechanics](https://github.com/AakaashfromIndia/OrbitalMechanics), набор из трёх Python-симуляций орбитальной механики.

## Пункты задания

| Пункт | Статус | Материалы |
| --- | --- | --- |
| 1. Только исследовать структуру проекта | Выполнено | [01_structure.md](01_structure.md), [log.md](log.md) |
| 2. Провести аудит научной корректности | Выполнено, статически | [02_audit.md](02_audit.md), [log.md](log.md) |
| 3. Создать собственный небольшой проект по шаблону курса | Не начат | Постановка и план будут оформлены отдельным этапом |

Подробные ограничения для дальнейшей работы записаны в [AGENTS.md](AGENTS.md). Исходное описание автора сохранено в [README-upstream.md](README-upstream.md).

## Исходный проект: запуск

Зависимости: NumPy, SciPy и Matplotlib. У исходного проекта нет закреплённых версий зависимостей и автоматических тестов. Для интерактивных окон нужен GUI-backend Matplotlib.

```powershell
pip install numpy scipy matplotlib
python "Two body system.py"
python "Hohmann Transfer.py"
python "Bielliptic Maneuver.py"
```

## Самопроверка студента

- [ ] Сверить отчёты с исходным кодом.
- [ ] Объяснить формулы задачи двух тел и орбитальных переходов.
- [ ] Сформулировать систему единиц и независимые проверки до реализации пункта 3.

