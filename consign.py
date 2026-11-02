import math

def cosine_similarity(a, b):
    # 1. 같은 칸끼리 곱해서 더하기 (SUMPRODUCT)
    dot = 0
    for i in range(len(a)):
        dot = dot +(a[i]*b[i])

    # 2. 각자의 길이
    len_a = math.sqrt(sum(x * x for x in a))
    len_b = math.sqrt(sum(x * x for x in b))

    return dot / (len_a * len_b)

print(cosine_similarity([1, 2], [3, 4]))
print(cosine_similarity([1, 2], [30, 40]))
print(cosine_similarity([1, 2], [-3, -4]))