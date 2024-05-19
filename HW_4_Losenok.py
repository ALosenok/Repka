# Задача 1. Решение Уравнения
import math as mth


def func(x):
    a = (mth.cos(mth.exp(x)) + mth.log((1+x)**2) +
        (mth.exp(mth.cos(x)) + mth.sin(mth.pi * x) ** 2) ** 0.5 +
        (1/x) ** 0.5 + mth.cos(x ** 2)) ** mth.sin(x)
    return a


var = 1.79

print(f"Ответ первой задачи {func(var)}")
# Улучшения для качества чтения?

# Задача 2. Search_substr


def search_substr(subst, st):
    subst = subst.lower()
    st = st.lower()
    if st.count(subst) > 0:
        resp = "Есть контакт!"
    else: resp = "Мимо!"
    return resp


a = "ab"
b = "fghghAbewewe"
print(f"Ответ второй задачи {search_substr(a, b)}")
