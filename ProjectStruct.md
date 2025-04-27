# Общая струтура

```bash
connection_service/
    ├── src/                                # Основной исходный код
    │   ├── abstract/
    │   │   └── interfacedef.py             # Абстрактные классы и интерфейсы
    │   ├── config.py                       # Конфигурация приложения
    │   ├── controller/
    │   │   └── signalpolicy.py             # Движок политик для адаптации к качеству сигнала
    │   ├── handlers/
    │   │   ├── abstract.py                 # Абстрактные классы для обработчиков
    │   │   ├── framedistributor.py         # Распределение кадров между потребителями
    │   │   ├── framehandler.py             # Обработчики кадров
    │   │   ├── inputsources.py             # Источники входных данных (FFMPEG, DepthAI)
    │   │   └── streamerFFmpegRTPS.py       # Потоковая передача через FFMPEG/RTP
    │   ├── network/
    │   │   ├── connection_checker.py       # Проверка сетевого соединения
    │   │   └── rciclient.py                # Клиент для работы с роутером Keenetic
    │   └── pkg/
    │       └── logger.py                   # Система логирования
    ├── main.py                             
    ├── main.conf
    ├── requirements.txt
    ├── Dockerfile
    ├── README.md
    └── .gitignore
```

## Основные компоненты

### Абстрактные интерфейсы (abstract/) 

определяют базовую структуру компонентов системы

> AbstractInputSource: интерфейс для источников входных видеоданных
> AbstractFrameDistributor: интерфейс для распределения кадров
> AbstractInputSource: Общий интерфей для обработки входного сигнала

### Обработчики видеопотоков (handlers/)

> FFMPEGInput: обработка потоковых данных через FFMPEG
> DAICameraInput: интеграция с камерами DepthAI
> FrameDistributor: распределение кадров между потребителями
> Сетевые компоненты (network/):

### ConnectionChecker: проверка доступности сети

> KeeneticRCIClient: взаимодействие с роутером для мониторинга качества соединения
> Контроллер качества (controller/):

### SignalPolicyEngine: регулировка параметров стрима в зависимости от качества сигнала
> Конфигурация (config.py):

### Config: загрузка и предоставление доступа к конфигурационным параметрам

> DeviceConfig: конфигурация устройств захвата видео
> Архитектура построена на принципах слабой связанности через абстрактные интерфейсы, что позволяет легко заменять компоненты и тестировать их изолированно.


# Интерфейсы обработчиков видео

```bash
src/handlers/
├── abstract.py                 # Базовые абстрактные классы
├── framedistributor.py         # Распределение кадров
├── framehandler.py             # Обработчики отдельных кадров
├── inputsources.py             # Источники видеоданных
└── streamerFFmpegRTPS.py       # RTPS стриминг через FFmpeg
```

## Основные интерфейсы

### AbstractInputSource
> Базовый интерфейс для всех источников видео
> ```python
> start(profile: dict) -> None  # Запуск с настройками профиля
> stop() -> None                # Остановка работы источника
> add_consumer(consumer_fn)     # Добавление функции-обработчика кадров
> remove_consumer(consumer_fn)  # Удаление функции-обработчика
> release() -> None             # Освобождение ресурсов (alias для stop)
> ```

### AbstractFrameProcessor
> Интерфейс для обработки отдельных кадров
> ```python
> process_frame(frame_bytes)    # Обработка и возврат модифицированного кадра
> release()                     # Освобождение ресурсов
> ```

### FrameDistributor
> Распределение кадров между потребителями
> ```python
> add_consumer(consumer_fn)     # Регистрация обработчика кадров
> remove_consumer(consumer_fn)  # Удаление обработчика
> distribute(frame_bytes)       # Отправка кадра всем зарегистрированным обработчикам
> ```

## Реализации

### Источники видео
> FFMPEGInput              # Получение видео через FFmpeg (RTSP, файлы, устройства)
> DAICameraInput           # Работа с камерами DepthAI/OAK
> WebcamInput              # Прямой доступ к веб-камерам через V4L2

### Обработчики
> EncodingFrameHandler     # Кодирование видео в разные форматы
> RecordingFrameHandler    # Запись видео в файлы
> AnalyticsFrameHandler    # Обработка для компьютерного зрения

### Стриминг
> RTSPStreamer             # Трансляция через RTSP протокол
> RTMPStreamer             # Трансляция по RTMP для стриминговых сервисов> start(profile: dict) -> None  # Запуск с настройками профиля
> stop() -> None                # Остановка работы источника
> add_consumer(consumer_fn)     # Добавление функции-обработчика кадров
> remove_consumer(consumer_fn)  # Удаление функции-обработчика
> release() -> None             # Освобождение ресурсов (alias для stop)
> ```


### AbstractFrameProcessor
> Интерфейс для обработки отдельных кадров
> ```python
> process_frame(frame_bytes)    # Обработка и возврат модифицированного кадра
> release()                     # Освобождение ресурсов
> ```

### FrameDistributor
> Распределение кадров между потребителями
> ```python
> add_consumer(consumer_fn)     # Регистрация обработчика кадров
> remove_consumer(consumer_fn)  # Удаление обработчика
> distribute(frame_bytes)       # Отправка кадра всем зарегистрированным обработчикам
> ```

## Реализации

### Источники видео
> FFMPEGInput              # Получение видео через FFmpeg (RTSP, файлы, устройства)
> DAICameraInput           # Работа с камерами DepthAI/OAK
> WebcamInput              # Прямой доступ к веб-камерам через V4L2

### Обработчики
> EncodingFrameHandler     # Кодирование видео в разные форматы
> RecordingFrameHandler    # Запись видео в файлы
> AnalyticsFrameHandler    # Обработка для компьютерного зрения

### Стриминг
> RTSPStreamer             # Трансляция через RTSP протокол
> RTMPStreamer             # Трансляция по RTMP для стриминговых сервисов