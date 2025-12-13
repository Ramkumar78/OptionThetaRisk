# Repository Coverage



| Name                                       |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------- | -------: | -------: | ------: | --------: |
| option\_auditor/\_\_init\_\_.py            |        2 |        0 |    100% |           |
| option\_auditor/cli.py                     |       57 |        0 |    100% |           |
| option\_auditor/common/constants.py        |        9 |        2 |     78% |   458-459 |
| option\_auditor/common/data\_utils.py      |       53 |       10 |     81% |39, 42-44, 61-63, 72-74 |
| option\_auditor/config.py                  |        4 |        0 |    100% |           |
| option\_auditor/journal\_analyzer.py       |       64 |        3 |     95% |104-105, 111 |
| option\_auditor/main\_analyzer.py          |      568 |       48 |     92% |190, 195, 242, 246-247, 274-276, 356, 410, 433, 441-442, 462, 483, 493-494, 498-499, 521-522, 553-554, 595-596, 604-613, 644, 677-680, 758-759, 763-765, 777-778, 862, 932 |
| option\_auditor/models.py                  |       75 |        2 |     97% |    76, 91 |
| option\_auditor/parsers.py                 |      266 |       16 |     94% |12, 33-38, 155, 191, 200, 204, 206-207, 328-329, 338 |
| option\_auditor/screener.py                |     1132 |      279 |     75% |22-23, 34, 59, 76, 80-82, 97-98, 114-117, 119-122, 142-144, 158, 214-216, 229, 234, 251-252, 266, 272, 310-312, 378, 381, 389, 459-465, 485-488, 490-493, 495-498, 500-501, 503-504, 513-515, 522, 544-545, 548, 581-584, 615-616, 623-629, 650-653, 655-658, 660-663, 665-666, 668-669, 678-680, 716-718, 734-737, 746-756, 760-763, 766-769, 790-792, 812-818, 837-840, 842-845, 847-850, 852-853, 855-856, 865-867, 874, 891, 954-968, 982-992, 1003-1058, 1066-1069, 1108, 1135-1137, 1163, 1173-1174, 1176-1178, 1195, 1207, 1370-1372, 1412, 1434, 1504, 1544-1546, 1647-1649, 1655-1657, 1670-1672, 1727-1728, 1770, 1776, 1815, 1858-1860, 1949, 1956-1957, 1966, 1994-1995, 1997-2000, 2016-2017, 2040-2043, 2052-2054, 2168-2170, 2172-2174, 2176-2178, 2189-2191, 2205-2206, 2231-2233, 2244-2290 |
| option\_auditor/sp500\_data.py             |        4 |        1 |     75% |        10 |
| option\_auditor/strategies/\_\_init\_\_.py |        0 |        0 |    100% |           |
| option\_auditor/strategies/base.py         |        6 |        1 |     83% |        28 |
| option\_auditor/strategies/fourier.py      |       34 |       17 |     50% |11, 17, 28-42 |
| option\_auditor/strategies/isa.py          |       46 |       17 |     63% |11, 32-36, 44-55 |
| option\_auditor/strategies/turtle.py       |       40 |        8 |     80% |11, 25, 38-43 |
| option\_auditor/strategies/utils.py        |       21 |        0 |    100% |           |
| option\_auditor/strategy.py                |      256 |        6 |     98% |16, 35, 155, 204, 208, 279 |
| option\_auditor/unified\_screener.py       |       80 |       20 |     75% |21-23, 34, 38-40, 57, 90-91, 97-102, 105-106, 125-127, 136 |
| webapp/app.py                              |      569 |      109 |     81% |83-84, 206, 218-219, 237-238, 291-292, 307-308, 313, 346-347, 356, 397, 411-412, 423, 427, 429, 451, 455, 460-462, 467-468, 479, 483, 485, 494-495, 499-524, 534, 549, 553, 555, 558-560, 565-566, 570-598, 613, 622-623, 665-666, 693-694, 713-715, 722-723, 745-753, 839-845 |
| webapp/storage.py                          |      391 |       29 |     93% |65, 69, 73, 77, 81, 85, 89, 93, 97, 101, 105, 109, 114, 267, 344-345, 420-421, 440-443, 460, 477-478, 489, 501-502, 521 |
|                                  **TOTAL** | **3677** |  **568** | **85%** |           |


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