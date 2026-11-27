"""Спільна підготовка для тестів: корінь проєкту в sys.path і тестовий токен."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ADMIN_TOKEN"] = "test-token"     # load_dotenv не перезапише це значення
