import re
import random

def spin(text: str) -> str:
    """
    Обрабатывает Spintax-разметку вида {вариант1|вариант2|вариант3}.
    Поддерживает вложенные конструкции.
    """
    pattern = re.compile(r'\{([^}]+)\}')
    result = text
    limit = 50  # защита от бесконечного цикла
    count = 0
    while pattern.search(result) and count < limit:
        result = pattern.sub(lambda m: random.choice(m.group(1).split('|')), result)
        count += 1
    return result
