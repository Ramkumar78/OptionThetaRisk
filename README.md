# Repository Coverage



| Name                                                |    Stmts |     Miss |   Cover |   Missing |
|---------------------------------------------------- | -------: | -------: | ------: | --------: |
| option\_auditor/\_\_init\_\_.py                     |        2 |        0 |    100% |           |
| option\_auditor/cli.py                              |       57 |       57 |      0% |     1-101 |
| option\_auditor/common/constants.py                 |        9 |        2 |     78% |   425-426 |
| option\_auditor/common/data\_utils.py               |      185 |       39 |     79% |24-25, 48-51, 77-81, 88-89, 93-97, 101-102, 106-107, 118-119, 157, 199-201, 213, 216-218, 235-237, 246-248, 300-301 |
| option\_auditor/common/resilience.py                |       10 |        0 |    100% |           |
| option\_auditor/common/signal\_type.py              |        6 |        0 |    100% |           |
| option\_auditor/config.py                           |        4 |        0 |    100% |           |
| option\_auditor/india\_stock\_data.py               |       32 |        5 |     84% |     40-45 |
| option\_auditor/journal\_analyzer.py                |       64 |        3 |     95% |104-105, 111 |
| option\_auditor/main\_analyzer.py                   |      568 |       49 |     91% |94-95, 190, 195, 242, 246-247, 274-276, 356, 410, 433, 441-442, 462, 483, 493-494, 498-499, 521-522, 553-554, 595-596, 604-613, 644, 677-680, 758-759, 763-765, 777-778, 862 |
| option\_auditor/master\_screener.py                 |      249 |       63 |     75% |47-51, 63, 69-71, 82-83, 97, 99-100, 112-113, 123-136, 151-153, 168-169, 182, 191-193, 210, 241, 250-255, 263-267, 283-294, 300, 321-322, 345-346, 372-374, 379 |
| option\_auditor/models.py                           |       75 |        2 |     97% |    76, 91 |
| option\_auditor/optimization.py                     |       94 |       22 |     77% |19-25, 30, 37-38, 57, 63-64, 70-71, 78-79, 95, 100, 162, 166-168 |
| option\_auditor/parsers.py                          |      269 |       16 |     94% |12, 33-38, 156, 192, 201, 205, 207-208, 330-331, 340 |
| option\_auditor/portfolio\_risk.py                  |      104 |       15 |     86% |63-66, 76-78, 82, 89, 118-125, 196 |
| option\_auditor/quant\_engine.py                    |      152 |       97 |     36% |14-65, 90-91, 119, 141-142, 149-158, 166-188, 195-232, 240-270 |
| option\_auditor/screener.py                         |     1683 |      355 |     79% |13-14, 40-41, 56-58, 70-72, 74, 95-142, 150, 162-164, 177, 183, 200-201, 223-226, 228-231, 252-256, 261-263, 276, 317-319, 327, 332, 350-351, 364-365, 371, 420-422, 476, 479, 552-555, 557-560, 562-565, 567-568, 570-571, 584-588, 593-595, 625-626, 629, 719-720, 747-750, 752-755, 757-760, 762-763, 765-766, 776-782, 787-789, 837-839, 867-877, 887-890, 907, 942-944, 982-985, 987-990, 992-995, 997-998, 1000-1001, 1011-1017, 1022-1024, 1040, 1105, 1108-1109, 1121-1125, 1128, 1131-1132, 1169-1171, 1181-1183, 1217, 1264-1265, 1267-1269, 1277-1279, 1389-1390, 1414-1416, 1427-1429, 1497, 1539-1540, 1575, 1584, 1666-1668, 1678, 1725-1728, 1732, 1772, 1784, 1804, 1856, 1868-1872, 1896, 1902, 1938-1940, 1976-1977, 2030-2031, 2042, 2141-2142, 2156-2157, 2164-2165, 2178-2179, 2188, 2190, 2196-2197, 2203, 2241, 2256, 2267, 2344-2345, 2362-2364, 2370-2372, 2380-2382, 2394-2395, 2428, 2435-2442, 2448, 2450, 2452, 2461-2463, 2482, 2490-2492, 2509-2510, 2528-2529, 2561, 2571-2622, 2646, 2663, 2668, 2701-2702, 2707-2708, 2742, 2761-2763, 2769-2770, 2774-2777, 2783, 2785, 2792, 2794, 2796, 2798, 2811-2813, 2837-2838, 2877, 2902-2903, 2943-2945 |
| option\_auditor/sp500\_data.py                      |       34 |        5 |     85% |31-32, 50-53 |
| option\_auditor/strategies/\_\_init\_\_.py          |        6 |        0 |    100% |           |
| option\_auditor/strategies/base.py                  |       17 |        4 |     76% |12, 20, 29-30 |
| option\_auditor/strategies/fourier.py               |       42 |       24 |     43% |11-44, 48, 54, 65-66 |
| option\_auditor/strategies/grandmaster\_screener.py |       64 |        8 |     88% |52-58, 117, 142 |
| option\_auditor/strategies/isa.py                   |       39 |        3 |     92% | 23, 86-88 |
| option\_auditor/strategies/turtle.py                |       34 |        4 |     88% | 17, 44-46 |
| option\_auditor/strategies/utils.py                 |       21 |       21 |      0% |      1-62 |
| option\_auditor/strategy.py                         |      256 |        6 |     98% |16, 35, 155, 204, 208, 279 |
| option\_auditor/uk\_stock\_data.py                  |       26 |        5 |     81% |     38-43 |
| option\_auditor/unified\_backtester.py              |      257 |       20 |     92% |35-37, 44, 144, 190, 263-264, 274-275, 279-280, 283-284, 301-306, 358-359 |
| option\_auditor/unified\_screener.py                |      146 |       97 |     34% |40-83, 93-221, 241-248, 256, 271-275, 297-298, 306 |
| option\_auditor/us\_stock\_data.py                  |       21 |       15 |     29% |     50-73 |
| webapp/app.py                                       |      909 |      271 |     70% |41-42, 81, 87, 102, 104, 107, 109, 151-152, 253-254, 294, 308-310, 329-344, 358-359, 369-370, 408-410, 426-427, 431, 461-463, 467-480, 491-492, 500-505, 512-513, 519, 525, 532-550, 558-560, 571, 575, 577, 579, 589-591, 603, 607, 609, 611, 613, 637, 641, 643, 647, 649-651, 657-659, 671, 675, 677, 679, 681, 689-691, 703, 707, 711, 713, 715-717, 723-725, 744-746, 761, 768-797, 801-830, 840, 869-871, 885, 889, 895-896, 907, 913-918, 935-940, 943-944, 962, 971, 973, 977-1004, 1007-1012, 1016-1018, 1033, 1043-1045, 1084-1085, 1110-1112, 1120-1132, 1151-1153, 1160-1161, 1183-1191, 1279-1285 |
| webapp/main.py                                      |       20 |       20 |      0% |      1-35 |
| webapp/storage.py                                   |      391 |       29 |     93% |65, 69, 73, 77, 81, 85, 89, 93, 97, 101, 105, 109, 114, 267, 344-345, 420-421, 440-443, 460, 477-478, 489, 501-502, 521 |
| **TOTAL**                                           | **5846** | **1257** | **78%** |           |


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