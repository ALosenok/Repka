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


# Задача 3. 3 наиболее встречаемых символа

from collections import Counter


def simbl_3(st):
    while st.count(" ") > 0:
        st = st.replace(" ", "")
    c = Counter(st)
    return c.most_common(3)


c = "rrr obr ppr"
print(f"Ответ третей задачи {simbl_3(c)}")

# Задача 4. Count_it


def count_it(sequence):
    slv = dict()
#    for i in sequence:
#        i = int(i)
#        if i in slv.keys():
#            slv[i] += 1
#        else: slv[i] = 1
    var_1 = Counter(sequence).most_common(3)
    for i,j in var_1:
        i = int(i)
        slv[i] = j
    return slv


seq = "124225555"
print(f"Ответ четвертой задачи {count_it(seq)}")


# Задача 5. Шахматы 1


def shah(l, m, n, o, p):
    ltr = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6, "g": 7, "h": 8}
    if p == "ферзь":
        if ltr[l] == ltr[n] or m == o:
            answ = "Угроза!"
        elif ltr[l] > ltr[n]:
            if o == m + ltr[l] - ltr[n] or o == m - ltr[l] - ltr[n]:
                answ = "Угроза!"
            else: answ = "Угрозы нет!"
        elif ltr[l] < ltr[n]:
            if o == m + ltr[n] - ltr[l] or o == m - ltr[n] - ltr[l]:
                answ = "Угроза!"
        else: answ = "Угрозы нет!"
    elif p == "конь":
        if (abs(ltr[l] - ltr[n]) == 1 and abs(m - o) == 2) or\
            (abs(ltr[l] - ltr[n]) == 2 and abs(m - o) == 1):
            answ = "Угроза!"
        else: answ = "Угрозы нет!"
    else: answ = "Угрозы нет!"
    return answ


print(f"Ответ пятой задачи {shah('h', 8, 'f', 7, 'конь')}")


# Задача 6. Шахматы 2.


def shah_2(l, m, n, o):
    ltr = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6, "g": 7, "h": 8}
    if (abs(ltr[l] - ltr[n]) == 1 and abs(m - o) == 2) or\
        (abs(ltr[l] - ltr[n]) == 2 and abs(m - o) == 1):
        answ = "Угроза в 1 ход!"
    elif (abs(ltr[l] - ltr[n]) in [2, 0] and abs(m - o) == 4) or\
        (abs(ltr[l] - ltr[n]) == 4 and abs(m - o) in [2, 0]):
        answ = "Угроза в 2 хода!"
    else: answ = "Угрозы нет!"

    return answ


print(f"Ответ шестой задачи {shah_2('e', 3, 'a', 1)}")
