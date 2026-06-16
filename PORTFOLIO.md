# Portfolio Text

## GitHub Repository Description

Lightweight Avito card parser: extracts public card fields from HTML without full browser rendering, exports CSV/JSON, saves progress, and measures cards/hour.

## LinkedIn Project Description

Built a lightweight marketplace card parser for Avito. The project focuses on increasing collection speed by avoiding full browser rendering for each card: it requests the HTML page, extracts public fields from HTML/embedded data, saves progress, exports CSV/JSON, and measures real cards/hour performance. Added adaptive delays and clear blocked/error statuses for stable long-running runs.

## Russian Case Description

Разработал легкий парсер карточек Авито для сбора публичных данных без полной браузерной загрузки каждой карточки. Основная оптимизация: получать HTML карточки и извлекать данные локально, не загружая изображения, шрифты, аналитику и клиентские скрипты. Добавлены экспорт в CSV/JSON, сохранение прогресса, адаптивные задержки, статусы ошибок/ограничений и расчет фактической скорости в карточках в час.

## Client Reply

Проверил подход и собрал тестовую реализацию. Вместо полной загрузки каждой карточки браузером парсер получает HTML карточки и извлекает основные поля локально. За счет этого не загружаются картинки, шрифты, аналитика и лишние скрипты, поэтому режим 90-100 карточек в час с одного IP выглядит достижимым при аккуратной задержке 36-42 секунды между карточками.

Финально скорость нужно подтвердить на ваших ссылках и полном списке нужных полей. Я добавил замер cards/hour, сохранение прогресса и адаптивную паузу при ошибках/ограничениях.

