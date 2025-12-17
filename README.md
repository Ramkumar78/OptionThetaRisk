# Repository Coverage



| Name                                       |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------- | -------: | -------: | ------: | --------: |
| option\_auditor/\_\_init\_\_.py            |        2 |        0 |    100% |           |
| option\_auditor/cli.py                     |       57 |        0 |    100% |           |
| option\_auditor/common/constants.py        |        9 |        2 |     78% |   458-459 |
| option\_auditor/common/data\_utils.py      |      142 |       36 |     75% |19-20, 36, 58-64, 71-72, 76-80, 87-88, 92-93, 105-106, 117-118, 148, 192-194, 206, 209-211, 228-230, 239-241 |
| option\_auditor/config.py                  |        4 |        0 |    100% |           |
| option\_auditor/india\_stock\_data.py      |        9 |        0 |    100% |           |
| option\_auditor/journal\_analyzer.py       |       64 |        3 |     95% |104-105, 111 |
| option\_auditor/main\_analyzer.py          |      568 |       48 |     92% |190, 195, 242, 246-247, 274-276, 356, 410, 433, 441-442, 462, 483, 493-494, 498-499, 521-522, 553-554, 595-596, 604-613, 644, 677-680, 758-759, 763-765, 777-778, 862, 932 |
| option\_auditor/models.py                  |       75 |        2 |     97% |    76, 91 |
| option\_auditor/optimization.py            |       94 |       22 |     77% |19-25, 30, 37-38, 57, 63-64, 70-71, 78-79, 95, 100, 162, 166-168 |
| option\_auditor/parsers.py                 |      269 |       16 |     94% |12, 33-38, 156, 192, 201, 205, 207-208, 330-331, 340 |
| option\_auditor/screener.py                |     1445 |      339 |     77% |22-23, 76-77, 90-92, 123, 125, 128-129, 149, 151, 155-158, 168, 180-182, 201-204, 221-222, 232-233, 249-252, 254-257, 286-298, 303-305, 319, 375-377, 390, 395, 413-414, 427-428, 434, 478-480, 534, 537, 635-638, 640-643, 645-648, 650-651, 653-654, 664-671, 676-678, 708-709, 712, 747-750, 799-800, 827-830, 832-835, 837-840, 842-843, 845-846, 856-862, 867-869, 917-919, 935-938, 947-957, 961-964, 967-970, 1005-1007, 1045-1048, 1050-1053, 1055-1058, 1060-1061, 1063-1064, 1074-1080, 1085-1087, 1112, 1176-1190, 1211-1221, 1232-1299, 1307-1310, 1349, 1413-1414, 1416-1418, 1427-1429, 1458, 1612-1613, 1633-1635, 1646-1648, 1712, 1786, 1817-1818, 1924-1925, 1958-1960, 2024, 2031-2032, 2074, 2080, 2136-2138, 2235-2236, 2270-2271, 2288-2289, 2291, 2317-2318, 2333-2334, 2341-2342, 2355-2356, 2369, 2371, 2378-2379, 2385, 2428, 2433, 2565-2566, 2591-2593, 2595-2597, 2599-2601, 2612-2614, 2628-2629, 2665-2667, 2680-2690, 2705-2707, 2720, 2731, 2740-2742, 2757-2758, 2760-2761, 2782-2783, 2810, 2820-2866 |
| option\_auditor/sp500\_data.py             |        4 |        1 |     75% |        11 |
| option\_auditor/strategies/\_\_init\_\_.py |        3 |        0 |    100% |           |
| option\_auditor/strategies/base.py         |        6 |        1 |     83% |        12 |
| option\_auditor/strategies/fourier.py      |       42 |        8 |     81% |48, 54, 61-66 |
| option\_auditor/strategies/isa.py          |       27 |        4 |     85% |     34-37 |
| option\_auditor/strategies/turtle.py       |       34 |        2 |     94% |     8, 17 |
| option\_auditor/strategies/utils.py        |       21 |       21 |      0% |      1-62 |
| option\_auditor/strategy.py                |      256 |        6 |     98% |16, 35, 155, 204, 208, 279 |
| option\_auditor/uk\_stock\_data.py         |        3 |        0 |    100% |           |
| option\_auditor/unified\_screener.py       |      114 |       33 |     71% |22-24, 35, 42-44, 47, 64, 97-98, 105-106, 112-113, 132-134, 143, 177, 183-201 |
| webapp/app.py                              |      693 |      147 |     79% |86-87, 209, 221-222, 240-241, 248, 281, 296-297, 312-313, 318, 351-352, 361, 402, 406, 408, 420-421, 432, 436, 438, 440, 462, 466, 468, 473-475, 480-481, 492, 496, 498, 500, 509-510, 522, 526, 530, 534-536, 541-542, 546-558, 568, 583, 587, 589, 591, 594-596, 601-602, 606-636, 648, 653, 660-661, 681-687, 713-724, 727, 747, 755, 759-765, 769-774, 778-779, 794, 803-804, 846-847, 874-875, 894-896, 903-904, 926-934, 1020-1026 |
| webapp/storage.py                          |      391 |       29 |     93% |65, 69, 73, 77, 81, 85, 89, 93, 97, 101, 105, 109, 114, 267, 344-345, 420-421, 440-443, 460, 477-478, 489, 501-502, 521 |
| **TOTAL**                                  | **4332** |  **720** | **83%** |           |


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