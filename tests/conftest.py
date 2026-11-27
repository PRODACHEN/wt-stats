"""Спільна підготовка для тестів: корінь проєкту в sys.path і тестовий ключ сесій."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SECRET_KEY"] = "test-secret"     # load_dotenv не перезапише це значення
