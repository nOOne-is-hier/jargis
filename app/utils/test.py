if __name__ == "__main__":
    sample = r"""
# 자기소개서 1 – [입행 목표 및 성장 계획]

**질문**
하나은행에 입행하여 이루고 싶은 목표와, 그 목표를 달성하기 위한 본인의 성장 계획을 작성해 주세요. (1,000자 이내)

**답변**
[신뢰를 주는 디지털 인재]
... 본문 ...

# 자기소개서 2 – [설득 경험과 강점·단점]

**질문**
의견 및 아이디어 등을 제안하면서, 누군가를 설득했던 경험을...

**답변**
[근거를 통해 신뢰를 얻다]
... 본문 ...
"""
    from md_parse import parse_md_blocks, extract_year_candidates

    blocks = parse_md_blocks(sample)
    for b in blocks:
        print("TITLE:", b["title"])
        print("Q:", b["question"][:50])
        print("A:", b["answer"][:50])
        print("---")
    print("YEARS:", extract_year_candidates(sample))
