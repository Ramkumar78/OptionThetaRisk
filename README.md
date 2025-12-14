# Repository Coverage



| Name                                       |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------- | -------: | -------: | ------: | --------: |
| option\_auditor/\_\_init\_\_.py            |        2 |        0 |    100% |           |
| option\_auditor/cli.py                     |       57 |        0 |    100% |           |
| option\_auditor/common/constants.py        |        9 |        2 |     78% |   458-459 |
| option\_auditor/common/data\_utils.py      |      108 |       20 |     81% |31-32, 39-40, 53-54, 84, 127-129, 141, 144-146, 163-165, 174-176 |
| option\_auditor/config.py                  |        4 |        0 |    100% |           |
| option\_auditor/journal\_analyzer.py       |       64 |        3 |     95% |104-105, 111 |
| option\_auditor/main\_analyzer.py          |      568 |       48 |     92% |190, 195, 242, 246-247, 274-276, 356, 410, 433, 441-442, 462, 483, 493-494, 498-499, 521-522, 553-554, 595-596, 604-613, 644, 677-680, 758-759, 763-765, 777-778, 862, 932 |
| option\_auditor/models.py                  |       75 |        2 |     97% |    76, 91 |
| option\_auditor/optimization.py            |       94 |       22 |     77% |19-25, 30, 37-38, 57, 63-64, 70-71, 78-79, 95, 100, 162, 166-168 |
| option\_auditor/parsers.py                 |      266 |       16 |     94% |12, 33-38, 155, 191, 200, 204, 206-207, 328-329, 338 |
| option\_auditor/screener.py                |     1327 |      325 |     76% |22-23, 43, 45, 48-49, 69, 71, 75-78, 88, 117-120, 137-138, 148-149, 165-168, 170-173, 192-194, 208, 264-266, 279, 284, 302-303, 317, 323, 363-365, 431, 434, 512-518, 538-541, 543-546, 548-551, 553-554, 556-557, 567-569, 576, 598-599, 602, 637-640, 673-674, 681-687, 708-711, 713-716, 718-721, 723-724, 726-727, 737-739, 780-782, 798-801, 810-820, 824-827, 830-833, 856-858, 878-884, 903-906, 908-911, 913-916, 918-919, 921-922, 932-934, 941, 958, 1021-1035, 1049-1059, 1070-1128, 1136-1139, 1178, 1205-1207, 1233, 1243-1244, 1246-1248, 1265, 1283, 1429-1430, 1458-1460, 1500, 1522, 1596, 1627-1628, 1751-1753, 1760-1762, 1775-1777, 1832-1833, 1875, 1881, 1920, 1964-1966, 2055, 2063-2064, 2073, 2098-2099, 2116-2117, 2119, 2141-2142, 2157-2158, 2165-2166, 2179-2180, 2193, 2195, 2202-2203, 2209, 2223-2226, 2242-2246, 2263, 2362-2363, 2388-2390, 2392-2394, 2396-2398, 2409-2411, 2425-2426, 2454-2456, 2469-2479, 2494-2496, 2509, 2520, 2529-2531, 2546-2547, 2549-2550, 2571-2572, 2587, 2597-2643 |
| option\_auditor/sp500\_data.py             |        4 |        1 |     75% |        10 |
| option\_auditor/strategies/\_\_init\_\_.py |        3 |        0 |    100% |           |
| option\_auditor/strategies/base.py         |        6 |        1 |     83% |        12 |
| option\_auditor/strategies/fourier.py      |       42 |        8 |     81% |48, 54, 61-66 |
| option\_auditor/strategies/isa.py          |       27 |        4 |     85% |     34-37 |
| option\_auditor/strategies/turtle.py       |       34 |        2 |     94% |     8, 17 |
| option\_auditor/strategies/utils.py        |       21 |       21 |      0% |      1-62 |
| option\_auditor/strategy.py                |      256 |        6 |     98% |16, 35, 155, 204, 208, 279 |
| option\_auditor/unified\_screener.py       |      114 |       33 |     71% |22-24, 35, 42-44, 47, 64, 97-98, 105-106, 112-113, 132-134, 143, 177, 183-201 |
| webapp/app.py                              |      582 |      120 |     79% |83-84, 206, 218-219, 237-238, 291-292, 307-308, 313, 346-347, 356, 397, 411-412, 423, 427, 429, 451, 455, 460-462, 467-468, 479, 483, 485, 494-495, 499-524, 528-540, 550, 565, 569, 571, 574-576, 581-582, 586-614, 629, 638-639, 681-682, 709-710, 729-731, 738-739, 761-769, 855-861 |
| webapp/storage.py                          |      391 |       29 |     93% |65, 69, 73, 77, 81, 85, 89, 93, 97, 101, 105, 109, 114, 267, 344-345, 420-421, 440-443, 460, 477-478, 489, 501-502, 521 |
|                                  **TOTAL** | **4054** |  **663** | **84%** |           |


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