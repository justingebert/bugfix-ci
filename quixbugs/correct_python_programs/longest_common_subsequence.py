def longest_common_subsequence(a, b):
    if not a or not b:
        return ""
    elif a[0] == b[0]:
        return a[0] + longest_common_subsequence(a[1:], b[1:])
    else:
        # Recursively compute both options and select the longer one
        seq1 = longest_common_subsequence(a, b[1:])
        seq2 = longest_common_subsequence(a[1:], b)
        return seq1 if len(seq1) > len(seq2) else seq2
