# Repository Coverage



| Name                                       |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------- | -------: | -------: | ------: | --------: |
| option\_auditor/\_\_init\_\_.py            |        2 |        0 |    100% |           |
| option\_auditor/cli.py                     |       57 |        0 |    100% |           |
| option\_auditor/common/constants.py        |       11 |        2 |     82% |   461-462 |
| option\_auditor/common/data\_utils.py      |      146 |       36 |     75% |20-21, 37, 59-65, 72-73, 77-81, 88-89, 93-94, 106-107, 118-119, 150, 210-212, 224, 227-229, 246-248, 257-259 |
| option\_auditor/common/resilience.py       |       10 |        0 |    100% |           |
| option\_auditor/config.py                  |        4 |        0 |    100% |           |
| option\_auditor/india\_stock\_data.py      |        9 |        0 |    100% |           |
| option\_auditor/journal\_analyzer.py       |       64 |        3 |     95% |104-105, 111 |
| option\_auditor/main\_analyzer.py          |      568 |       48 |     92% |190, 195, 242, 246-247, 274-276, 356, 410, 433, 441-442, 462, 483, 493-494, 498-499, 521-522, 553-554, 595-596, 604-613, 644, 677-680, 758-759, 763-765, 777-778, 862, 932 |
| option\_auditor/models.py                  |       75 |        2 |     97% |    76, 91 |
| option\_auditor/optimization.py            |       94 |       22 |     77% |19-25, 30, 37-38, 57, 63-64, 70-71, 78-79, 95, 100, 162, 166-168 |
| option\_auditor/parsers.py                 |      269 |       16 |     94% |12, 33-38, 156, 192, 201, 205, 207-208, 330-331, 340 |
| option\_auditor/portfolio\_risk.py         |       95 |       14 |     85% |39, 63-69, 99-106, 177-181 |
| option\_auditor/screener.py                |     1508 |      347 |     77% |22-23, 76-77, 90-92, 123, 125, 128-129, 149, 151, 155-158, 168, 180-182, 201-204, 221-222, 232-233, 249-252, 254-257, 286-298, 303-305, 319, 375-377, 390, 395, 413-414, 427-428, 434, 478-480, 534, 537, 635-638, 640-643, 645-648, 650-651, 653-654, 664-671, 676-678, 708-709, 712, 747-750, 800-801, 828-831, 833-836, 838-841, 843-844, 846-847, 857-863, 868-870, 918-920, 936-939, 948-958, 962-965, 968-971, 1006-1008, 1046-1049, 1051-1054, 1056-1059, 1061-1062, 1064-1065, 1075-1081, 1086-1088, 1113, 1177-1191, 1212-1222, 1233-1300, 1308-1311, 1350, 1414-1415, 1417-1419, 1428-1430, 1459, 1613-1614, 1634-1636, 1647-1649, 1713, 1787, 1818-1819, 1925-1926, 1959-1961, 2025, 2032-2033, 2075, 2081, 2137-2139, 2236-2237, 2271-2272, 2289-2290, 2292, 2318-2319, 2334-2335, 2342-2343, 2356-2357, 2370, 2372, 2379-2380, 2386, 2429, 2434, 2566-2567, 2592-2594, 2596-2598, 2600-2602, 2613-2615, 2629-2630, 2666-2668, 2681-2691, 2701, 2709-2711, 2724, 2735, 2744-2746, 2761-2762, 2764-2765, 2786-2787, 2814, 2824-2870, 2904, 2940, 2962-2963, 2968-2969, 2993 |
| option\_auditor/sp500\_data.py             |        4 |        1 |     75% |        11 |
| option\_auditor/strategies/\_\_init\_\_.py |        3 |        0 |    100% |           |
| option\_auditor/strategies/base.py         |       17 |        4 |     76% |12, 20, 29-30 |
| option\_auditor/strategies/fourier.py      |       42 |        8 |     81% |48, 54, 61-66 |
| option\_auditor/strategies/isa.py          |       27 |        4 |     85% |     34-37 |
| option\_auditor/strategies/turtle.py       |       34 |        2 |     94% |     8, 17 |
| option\_auditor/strategies/utils.py        |       21 |       21 |      0% |      1-62 |
| option\_auditor/strategy.py                |      256 |        6 |     98% |16, 35, 155, 204, 208, 279 |
| option\_auditor/uk\_stock\_data.py         |        3 |        0 |    100% |           |
| option\_auditor/unified\_screener.py       |      114 |       33 |     71% |22-24, 35, 42-44, 47, 64, 97-98, 105-106, 112-113, 132-134, 143, 177, 183-201 |
| webapp/app.py                              |      744 |      183 |     75% |88-89, 211, 223-224, 253-254, 261, 294, 309-310, 325-326, 331, 364-365, 369-381, 390, 431, 435, 437, 449-450, 461, 465, 467, 469, 491, 495, 497, 502-504, 509-510, 521, 525, 527, 529, 538-539, 551, 555, 559, 563-565, 570-571, 575-587, 597, 612, 616, 618, 620, 623-625, 630-631, 635-665, 677, 682, 689-690, 713, 719-724, 750-755, 758, 779, 789, 791, 795-832, 836-841, 845-846, 861, 870-871, 913-914, 941-942, 950-961, 979-981, 988-989, 1011-1019, 1105-1111 |
| webapp/storage.py                          |      391 |       29 |     93% |65, 69, 73, 77, 81, 85, 89, 93, 97, 101, 105, 109, 114, 267, 344-345, 420-421, 440-443, 460, 477-478, 489, 501-502, 521 |
| **TOTAL**                                  | **4568** |  **781** | **83%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://github.com/Ramkumar78/OptionThetaRisk/raw/python-coverage-comment-action-data/badge.svg)](https://github.com/Ramkumar78/OptionThetaRisk/tree/python-coverage-comment-action-data)

This is the one to use if your repository is private or if you don't want to customize anything.



## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.