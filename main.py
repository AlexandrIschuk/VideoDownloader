import yt_dlp
from PyQt6.QtWidgets import QApplication, QPushButton, QMainWindow, QTextEdit, QVBoxLayout, QWidget, QLineEdit, \
    QFileDialog, QHBoxLayout, QMessageBox, QProgressBar, QLabel, QComboBox
from PyQt6.QtCore import QSize, pyqtSignal, QThread, Qt
from PyQt6.QtGui import QTextCursor
import sys
import os
import threading


# Класс для скачивания в отдельном потоке
class DownloadThread(QThread):
    # Сигналы для обновления UI
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, url, output_path, quality='best'):
        super().__init__()
        self.url = url
        self.output_path = output_path
        self.quality = quality
        self.stop_flag = False

    def run(self):
        try:
            # Функция для обработки прогресса
            def progress_hook(d):
                if self.stop_flag:
                    raise Exception("Скачивание отменено")

                if d['status'] == 'downloading':
                    # Получаем процент выполнения
                    if '_percent_str' in d:
                        percent_str = d['_percent_str'].replace('%', '').strip()
                        try:
                            percent = float(percent_str)
                            self.progress_signal.emit(int(percent), f"Скачивание: {percent_str}%")
                        except:
                            pass
                    elif 'total_bytes' in d and d['total_bytes']:
                        percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                        self.progress_signal.emit(int(percent), f"Скачивание: {percent:.1f}%")
                    else:
                        self.progress_signal.emit(0, "Скачивание...")

                elif d['status'] == 'finished':
                    self.progress_signal.emit(100, "Обработка видео...")

            # Настройки yt-dlp
            ydl_opts = {
                'outtmpl': f'{self.output_path}/%(title)s.%(ext)s',
                'format': self.quality,
                'progress_hooks': [progress_hook],
                'quiet': True,
                'no_warnings': True,
            }

            self.log_signal.emit("Начинаем скачивание...")
            self.log_signal.emit(f"URL: {self.url}")
            self.log_signal.emit(f"Папка: {self.output_path}")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Получаем информацию о видео (без скачивания)
                info = ydl.extract_info(self.url, download=False)
                title = info.get('title', 'Неизвестное видео')
                duration = info.get('duration', 0)

                self.log_signal.emit(f"Найдено видео: {title}")
                self.log_signal.emit(f"Длительность: {duration} секунд")
                self.log_signal.emit("Начинаем скачивание...")

                # Скачиваем видео
                ydl.download([self.url])

                self.log_signal.emit("Скачивание завершено успешно!")
                self.finished_signal.emit(True, "Готово!")

        except Exception as e:
            error_msg = f"Ошибка: {str(e)}"
            self.log_signal.emit(error_msg)
            self.finished_signal.emit(False, error_msg)

    def stop(self):
        self.stop_flag = True


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.download_thread = None
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.setWindowTitle("Скачать видео")

        # Создаем кнопку скачивания
        self.selfbutton = QPushButton("Скачать")
        self.selfbutton.setFixedHeight(40)

        self.quality_combo = QComboBox()
        self.quality_combo.addItem("Лучшее качество", "best")
        self.quality_combo.addItem("Хорошее качество", "best[height<=1080]")
        self.quality_combo.addItem("Среднее качество", "best[height<=720]")
        self.quality_combo.addItem("Низкое качество", "best[height<=480]")
        self.quality_combo.addItem("Только аудио", "bestaudio")

        # Поле для URL
        self.url_text = QLineEdit()
        self.url_text.setPlaceholderText("Ссылка на видео...")

        # Поле для пути и кнопка обзора
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Путь к папке...")
        # Устанавливаем папку загрузок по умолчанию
        self.path_edit.setText(os.path.expanduser("~/Downloads"))

        self.browse_button = QPushButton("Обзор")
        self.browse_button.setFixedWidth(100)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(25)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 2px;
                text-align: center;
                font-weight: bold;
                padding: 1px;
            }

            QProgressBar::chunk {
                background-color: #4CAF50;  /* Зеленый цвет */
                border-radius: 2px;
            }
        """)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        # Метка статуса
        self.status_label = QLabel("Готов к работе")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Текстовое поле для лога
        self.errlb = QTextEdit()
        self.errlb.setReadOnly(True)
        self.errlb.setMaximumHeight(150)
        self.errlb.setPlaceholderText("Здесь будет отображаться лог скачивания...")

        # Горизонтальный layout для пути
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.path_edit)
        h_layout.addWidget(self.browse_button)

        # Добавляем все элементы в layout
        self.layout.addWidget(QLabel("Ссылка на видео:"))
        self.layout.addWidget(self.url_text)
        self.layout.addWidget(QLabel("Качество видео:"))
        self.layout.addWidget(self.quality_combo)
        self.layout.addWidget(QLabel("Папка для сохранения:"))
        self.layout.addLayout(h_layout)
        self.layout.addWidget(self.selfbutton)
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(QLabel("Лог выполнения:"))
        self.layout.addWidget(self.errlb)

        # Устанавливаем фиксированный размер окна
        self.setFixedSize(QSize(450, 500))

        widget = QWidget()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        # Подключаем сигналы
        self.browse_button.clicked.connect(self.select_directory)
        self.selfbutton.clicked.connect(self.start_download)

    def select_directory(self):
        # Открываем диалог выбора папки
        directory = QFileDialog.getExistingDirectory(self, "Выберите папку", "")
        if directory:
            self.path_edit.setText(directory)

    def append_log(self, message):
        """Добавляет сообщение в лог"""
        self.errlb.append(message)
        # Автоматически прокручиваем к новому сообщению
        cursor = self.errlb.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.errlb.setTextCursor(cursor)
        self.errlb.ensureCursorVisible()

        # Обновляем UI
        QApplication.processEvents()

    def start_download(self):
        # Если идет скачивание, останавливаем его
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop()
            self.download_thread.wait()
            self.selfbutton.setText("Скачать")
            return

        url = self.url_text.text().strip()
        output_path = self.path_edit.text().strip()

        # Проверяем ввод
        if not url:
            QMessageBox.warning(self, "Ошибка", "Введите URL видео")
            return

        if not output_path:
            QMessageBox.warning(self, "Ошибка", "Выберите папку для сохранения")
            return

        # Очищаем лог и сбрасываем прогресс
        self.errlb.clear()
        self.progress_bar.setValue(0)

        quality = self.quality_combo.currentData()

        # Создаем и настраиваем поток скачивания
        self.download_thread = DownloadThread(url, output_path, quality)

        # Подключаем сигналы
        self.download_thread.log_signal.connect(self.append_log)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.download_finished)

        # Меняем кнопку на "Отмена"
        self.selfbutton.setText("Отмена")

        # Запускаем поток
        self.download_thread.start()

    def update_progress(self, percent, message):
        """Обновляет прогресс-бар и статус"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

        # Если есть прогресс, добавляем в лог (но не слишком часто)
        if percent % 25 == 0 or percent == 100:
            self.append_log(message)

    def download_finished(self, success, message):
        self.selfbutton.setText("Скачать")

        if success:
            self.status_label.setText("Скачивание завершено!")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.append_log("✓ " + message)

            reply = QMessageBox.information(
                self, 'Статус',
                'Видео успешно скачано!',
                QMessageBox.StandardButton.Ok
            )

            os.startfile(self.path_edit.text())

        else:
            self.status_label.setText("Ошибка!")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.append_log("✗ " + message)
            QMessageBox.critical(self, "Ошибка", message)

        # Сбрасываем прогресс-бар через 3 секунды
        threading.Timer(3.0, lambda: self.progress_bar.setValue(0)).start()

    def closeEvent(self, event):
        """Обрабатывает закрытие окна - останавливает поток если работает"""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop()
            self.download_thread.wait()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec())