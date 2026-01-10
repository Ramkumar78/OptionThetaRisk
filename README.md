# Repository Coverage



| Name                                       |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------- | -------: | -------: | ------: | --------: |
| option\_auditor/\_\_init\_\_.py            |        2 |        0 |    100% |           |
| option\_auditor/cli.py                     |       57 |       57 |      0% |     1-101 |
| option\_auditor/common/constants.py        |        9 |        2 |     78% |   425-426 |
| option\_auditor/common/data\_utils.py      |      185 |       39 |     79% |24-25, 48-51, 77-81, 88-89, 93-97, 101-102, 106-107, 118-119, 157, 199-201, 213, 216-218, 235-237, 246-248, 300-301 |
| option\_auditor/common/resilience.py       |       10 |        0 |    100% |           |
| option\_auditor/common/signal\_type.py     |        6 |        0 |    100% |           |
| option\_auditor/config.py                  |        4 |        0 |    100% |           |
| option\_auditor/india\_stock\_data.py      |       32 |        5 |     84% |     40-45 |
| option\_auditor/journal\_analyzer.py       |       64 |        3 |     95% |104-105, 111 |
| option\_auditor/main\_analyzer.py          |      568 |       50 |     91% |94-95, 190, 195, 242, 246-247, 274-276, 356, 410, 433, 441-442, 462, 483, 493-494, 498-499, 521-522, 553-554, 595-596, 604-613, 644, 677-680, 758-759, 763-765, 777-778, 862, 932 |
| option\_auditor/master\_screener.py        |      249 |       64 |     74% |47-51, 69-71, 82-83, 97, 99-100, 112-113, 123-136, 151-153, 168-169, 182, 191-193, 210, 241, 250-255, 263-267, 270-272, 284-294, 300, 321-322, 345-346, 372-374, 379 |
| option\_auditor/models.py                  |       75 |        2 |     97% |    76, 91 |
| option\_auditor/optimization.py            |       94 |       22 |     77% |19-25, 30, 37-38, 57, 63-64, 70-71, 78-79, 95, 100, 162, 166-168 |
| option\_auditor/parsers.py                 |      269 |       16 |     94% |12, 33-38, 156, 192, 201, 205, 207-208, 330-331, 340 |
| option\_auditor/portfolio\_risk.py         |      104 |       15 |     86% |63-66, 76-78, 82, 89, 118-125, 196 |
| option\_auditor/quant\_engine.py           |      152 |       97 |     36% |14-65, 90-91, 119, 141-142, 149-158, 166-188, 195-232, 240-270 |
| option\_auditor/screener.py                |     1676 |      359 |     79% |13-14, 40-41, 56-58, 70-72, 74, 95-142, 150, 162-164, 177, 183, 200-201, 223-226, 228-231, 252-256, 261-263, 276, 317-319, 327, 332, 350-351, 364-365, 371, 420-422, 476, 479, 552-555, 557-560, 562-565, 567-568, 570-571, 584-588, 593-595, 625-626, 629, 719-720, 747-750, 752-755, 757-760, 762-763, 765-766, 776-782, 787-789, 837-839, 867-877, 887-890, 907, 942-944, 982-985, 987-990, 992-995, 997-998, 1000-1001, 1011-1017, 1022-1024, 1040, 1083-1085, 1101-1109, 1121-1125, 1128, 1131-1132, 1169-1171, 1181-1183, 1217, 1264-1265, 1267-1269, 1277-1279, 1389-1390, 1414-1416, 1427-1429, 1497, 1539-1540, 1575, 1584, 1666-1668, 1678, 1725-1728, 1732, 1772, 1784, 1804, 1859-1860, 1884, 1890, 1926-1928, 1964-1965, 2018-2019, 2030, 2129-2130, 2144-2145, 2152-2153, 2166-2167, 2176, 2178, 2184-2185, 2191, 2229, 2244, 2255, 2332-2333, 2350-2352, 2358-2360, 2368-2370, 2382-2383, 2416, 2423-2430, 2436, 2438, 2440, 2449-2451, 2470, 2478-2480, 2497-2498, 2516-2517, 2549, 2559-2610, 2634, 2651, 2656, 2689-2690, 2695-2696, 2730, 2749-2751, 2757-2758, 2762-2765, 2771, 2773, 2780, 2782, 2784, 2786, 2799-2801, 2825-2826, 2865, 2890-2891, 2931-2933 |
| option\_auditor/sp500\_data.py             |       34 |        5 |     85% |31-32, 50-53 |
| option\_auditor/strategies/\_\_init\_\_.py |        6 |        0 |    100% |           |
| option\_auditor/strategies/base.py         |       17 |        4 |     76% |12, 20, 29-30 |
| option\_auditor/strategies/fourier.py      |       42 |       24 |     43% |11-44, 48, 54, 65-66 |
| option\_auditor/strategies/grandmaster.py  |       49 |       13 |     73% |29, 50-57, 117-124 |
| option\_auditor/strategies/isa.py          |       35 |        3 |     91% | 21, 76-78 |
| option\_auditor/strategies/turtle.py       |       34 |        4 |     88% | 17, 44-46 |
| option\_auditor/strategies/utils.py        |       21 |       21 |      0% |      1-62 |
| option\_auditor/strategy.py                |      256 |        6 |     98% |16, 35, 155, 204, 208, 279 |
| option\_auditor/uk\_stock\_data.py         |       26 |        5 |     81% |     38-43 |
| option\_auditor/unified\_backtester.py     |      236 |       19 |     92% |35-37, 44, 168, 241-242, 252-253, 257-258, 261-262, 279-284, 335-336 |
| option\_auditor/unified\_screener.py       |      146 |       97 |     34% |40-83, 93-221, 241-248, 256, 271-275, 297-298, 306 |
| option\_auditor/us\_stock\_data.py         |       21 |       15 |     29% |     50-73 |
| webapp/app.py                              |      889 |      253 |     72% |41-42, 81, 87, 102, 104, 107, 109, 151-152, 253-254, 294, 308-310, 329-344, 358-359, 369-370, 408-410, 426-427, 431, 461-463, 467-480, 493-494, 500-501, 508-509, 516-518, 529, 533, 535, 537, 547-549, 561, 565, 567, 569, 571, 595, 599, 601, 605, 607-609, 615-617, 629, 633, 635, 637, 639, 647-649, 661, 665, 669, 671, 673-675, 681-683, 702-704, 719, 726-755, 759-788, 798, 827-829, 843, 847, 853-854, 865, 871-876, 893-898, 901-902, 920, 929, 931, 935-962, 965-970, 974-976, 991, 1001-1003, 1042-1043, 1068-1070, 1078-1090, 1109-1111, 1118-1119, 1141-1149, 1237-1243 |
| webapp/main.py                             |       20 |       20 |      0% |      1-35 |
| webapp/storage.py                          |      391 |       29 |     93% |65, 69, 73, 77, 81, 85, 89, 93, 97, 101, 105, 109, 114, 267, 344-345, 420-421, 440-443, 460, 477-478, 489, 501-502, 521 |
| **TOTAL**                                  | **5779** | **1249** | **78%** |           |


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