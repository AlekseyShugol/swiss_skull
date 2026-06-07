import traceback
from datetime import datetime
from functools import wraps

class Logger:
    """Система логирования с выводом в консоль и файл."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.log_file = "logs.txt"
        self._init_log_file()

    def _init_log_file(self):
        """Инициализация файла логов."""
        try:
            with open(self.log_file, 'a+', encoding='utf-8') as f:
                f.write(f"{'=' * 80}\n")
                f.write(f"LOG STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'=' * 80}\n\n")
        except Exception as e:
            print(f"Warning: Could not create log file: {e}")

    def _write(self, level, message, include_traceback=False):
        """Запись сообщения в консоль и файл."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}"

        # Вывод в консоль
        print(log_entry)

        # Запись в файл
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
                if include_traceback:
                    f.write(traceback.format_exc() + '\n')
        except Exception as e:
            print(f"Warning: Could not write to log file: {e}")

    def info(self, message):
        """Информационное сообщение."""
        self._write("INFO", message)

    def warning(self, message):
        """Предупреждение."""
        self._write("WARNING", message)

    def error(self, message, include_traceback=True):
        """Ошибка с traceback."""
        self._write("ERROR", message, include_traceback)

    def debug(self, message):
        """Отладочное сообщение."""
        self._write("DEBUG", message)

    def action(self, action_name, details=""):
        """Логирование действия пользователя."""
        msg = f"ACTION: {action_name}"
        if details:
            msg += f" | {details}"
        self._write("ACTION", msg)

    def separator(self):
        """Разделитель в логе."""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'-' * 80}\n\n")
        except:
            pass
        print("-" * 80)


def log_method(logger_instance):
    """Декоратор для логирования вызовов методов."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            class_name = args[0].__class__.__name__ if args else "Unknown"
            method_name = func.__name__
            logger_instance.debug(f"Calling {class_name}.{method_name}()")
            try:
                result = func(*args, **kwargs)
                logger_instance.debug(f"Completed {class_name}.{method_name}()")
                return result
            except Exception as e:
                logger_instance.error(f"Exception in {class_name}.{method_name}: {str(e)}", include_traceback=True)
                raise

        return wrapper

    return decorator


log = Logger()