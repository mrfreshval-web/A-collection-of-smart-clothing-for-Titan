# 05-design · Источники

Дата проверки ссылок: 2026-11-28. Отдел «Дизайн» ссылается на источники так:

| Формат ссылки | Где список | Пример |
|---|---|---|
| **[D№]** | этот файл (новые источники отдела «Дизайн») | [D1] |
| **[T-S№]** | [../04-tech/99-sources.md](../04-tech/99-sources.md) (отдел «Технологии») | [T-S16] — стандарт стирки e-textile |
| **[R-S№]** | [../01-research/sources.md](../01-research/sources.md) (Стратегия, рынок) | [R-S42] — обзор перчаток с подогревом |
| **[N№]** | [../00-vision/north-star-sources.md](../00-vision/north-star-sources.md) | [N14] — карты термочувствительности тела |
| **[Sci: Ключ]** | [../03-science/references.md](../03-science/references.md) | [Sci: Moritz1947] |

Префиксы T- и R- нужны, потому что «Технологии» и «Стратегия» независимо нумеруют источники как S№, и номера пересекаются.

**[Гипотеза]** — оценка отдела, требует проверки. **[Решение дизайна]** — предложение отдела, которое утверждают основатель и смежные отделы. **[Расчёт]** — выведено из цифр источников, ход показан.

## Тело: пот, зоны, размещение

- **[D1]** Smith C.J., Havenith G. *Body mapping of sweating patterns in male athletes in mild exercise-induced hyperthermia.* Eur J Appl Physiol. 2011;111(7):1391–1404. doi:10.1007/s00421-010-1744-8. Мужчины, 25 °C, 50 % RH, 75 % VO2max: наибольшее потоотделение — центр верхней и средней спины и поясница (значения 1 197, 1 148 и 856 г/м²·ч), лоб 1 710 г/м²·ч; наименьшее — пальцы, большие пальцы, ладони (144, 254, 119 г/м²·ч). https://pubmed.ncbi.nlm.nih.gov/21153660/
- **[D2]** Smith C.J., Havenith G. *Body mapping of sweating patterns in athletes: a sex comparison.* Рукопись в репозитории Loughborough University (журнальные выходные данные в доступной копии не указаны, **[сверить]**). 13 женщин и 9 мужчин, 25 °C: у женщин при 75 % VO2max максимум — центр верхней спины (723 г/м²·ч), «треугольник бра» между грудями (470), поясница (333); минимум — грудь и боковые части спины. У мужчин абсолютное потоотделение выше; у женщин больше доля пота на руках и кистях. https://repository.lboro.ac.uk/articles/Body_mapping_of_sweating_patterns_in_athletes_a_sex_comparison/9348068/files/16957136.pdf
- **[D9]** Sorysz и др. *Beyond the Pocket: a large-scale international study on user preferences on bodily placements of commercial wearables.* arXiv:2509.25383, 2025. n = 320: мужчины чаще носят смартфон в переднем кармане брюк, женщины — в заднем кармане или в кармане куртки на уровне талии; часы — на левом (недоминантном) запястье. https://arxiv.org/html/2509.25383v1

## Горы: лавинные датчики

- **[D3]** Klassen K. *Mitigating avalanche transceiver interference.* Avalanche Canada, 09.12.2021. Режим передачи: источники помех не ближе 20 см (автор сам держит 30–40 см); поиск: 50 см. Куртки с подогревом — «точно нет»; носки с подогревом — «вероятно, допустимо» в режиме передачи, но выключать при поиске; перчатки с подогревом или фольгой — избегать. https://avalanche.ca/fr/blogs/mitigating-avalanche-transceiver-interference
- **[D4]** UIAA. *Avalanche Beacons Recommendation*, V1, 26.10.2023. Передача: > 20 см от электроники, металла, металлизированной фольги, магнитов и **нагревательных элементов**. Поиск: всё выключить, «снять перчатки с подогревом», «выключить носки и ботинки с подогревом»; > 50 см от нужных устройств (фонарь); > 10 м от включённого телефона и радио. https://www.theuiaa.org/documents/safety/UIAA-Avalanche-Beacons-Recommendation.pdf

## Цвет и доступность

- **[D8]** Washington University in St. Louis, *Color blindness* (со ссылками на Deeb 2005, Clinical Genetics; Katsnelson 2021, Nature): нарушения цветового зрения — до 8 % мужчин и 0,5 % женщин; совет избегать пар «красный — зелёный». https://sites.wustl.edu/inclusion/how-to-be-inclusive/color-blindness

## Приложение и платформа

- **[D7]** Android Developers, *Progress-centric notifications* (Android 16, обновлено 03.03.2026): `Notification.ProgressStyle` с точками и сегментами для отслеживания пути «от начала до конца» (такси, доставка, навигация). https://developer.android.com/about/versions/16/features/progress-centric-notifications

## Устойчивость и нормативка изделия

- **[D5]** European Commission, *Digital Product Passport — textile apparel*: «Q4 2027 — плановое принятие делегированного акта ESPR для текстиля»; сроки могут меняться. https://single-market-economy.ec.europa.eu/single-market/digital-product-passport/textile-apparel_en
- **[D6]** EU Circular Economy Stakeholder Platform, *DPP timeline 2026–2030* (09.10.2026): принятие акта по текстилю ожидается в 2027 году, требования DPP распространяются на текстиль постепенно в 2028–2030. https://circulareconomy.europa.eu/node/10371

## Внутренние источники проекта

- **[D10]** Тизер «Изотерма»: [../08-gtm/social/teaser-2026-11/design-philosophy.md](../08-gtm/social/teaser-2026-11/design-philosophy.md) и README той же папки (ограничение на раскрытие устройства продукта до патентной заявки).
- **[D11]** Креативный бриф кампании «Твой климат. Везде.», версия 2 от 26.11.2026 (`08-gtm/social/campaign-teaser/creative-brief.md`, PR кампании; копия в файлах проекта `instagram-teaser/creative-brief.md`).

## Чего в списке нет

- Бренд-бук экосистемы в репозитории `health-of-a-titan` (папка `brand/`) отделу недоступен из этой сессии. Цвета и шрифты в [01-brand-visual-language.md](01-brand-visual-language.md) сняты с утверждённых тизеров [D10][D11] и требуют сверки с бренд-буком **[сверить]**.
