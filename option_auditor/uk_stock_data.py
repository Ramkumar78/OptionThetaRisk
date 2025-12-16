
# Top 350 UK Stocks (LSE) by Market Cap
# Scraped from Yahoo Finance

UK_350_TICKERS = [
    "TYT.L", "AZN.L", "HSBA.L", "SHEL.L", "BNC.L", "BP-A.L", "BHP.L", "BP-B.L", "ULVR.L", "BATS.L", 
    "RIO.L", "RR.L", "GSK.L", "LLOY.L", "IHG.L", "NXT.L", "VALT.L", "0R0X.L", "IPC.L", "SWR.L", 
    "ABF.L", "LGEN.L", "CCH.L", "CKI.L", "HLMA.L", "SMT.L", "AAF.L", "INF.L", "0Q1F.L", "ZEG.L", 
    "0R37.L", "RTO.L", "SGE.L", "SN.L", "ADM.L", "SGRO.L", "STAN.L", "WPP.L", "EXPN.L", "0R3F.L", 
    "PRU.L", "LAND.L", "RMV.L", "AV.L", "ANTO.L", "AVV.L", "PSN.L", "0R3E.L", "IMI.L", "0R3A.L", 
    "BKG.L", "MNG.L", "REL.L", "CRH.L", "GLEN.L", "TW.L", "NG.L", "RS1.L", "WTB.L", "FLTR.L", 
    "DCC.L", "AAL.L", "DGE.L", "BME.L", "BNK.L", "KGF.L", "0R30.L", "IAG.L", "CPG.L", "0R32.L", 
    "III.L", "RKT.L", "BDEV.L", "SSE.L", "FRES.L", "0R31.L", "BA.L", "BARC.L", "ENT.L", "0R2Y.L", 
    "SPX.L", "IGG.L", "CRDA.L", "0R2Z.L", "CNA.L", "MERL.L", "FRAS.L", "SVT.L", "RSA.L", "HL.L", 
    "SKG.L", "UTG.L", "0R39.L", "SMIN.L", "WEIR.L", "0LEA.L", "SBRY.L", "DPLM.L", "BNZL.L", "MRO.L", 
    "STJ.L", "ITRK.L", "PHNX.L", "PSON.L", "0QZ0.L", "ECM.L", "OCDO.L", "0I20.L", "0R34.L", "SMDS.L", 
    "SRE.L", "0R3B.L", "FGP.L", "EZJ.L", "AUTO.L", "RSW.L", "SKIN.L", "0M68.L", "0QYY.L", "0R35.L", 
    "DRX.L", "0A63.L", "0QQG.L", "ASC.L", "0O24.L", "BT-A.L", "GVC.L", "EVR.L", "0R2N.L", "CTEC.L", 
    "HLN.L", "PHG.L", "IAP.L", "0R2P.L", "MKS.L", "RSE.L", "SDR.L", "MGAM.L", "TUI.L", "0R2R.L", 
    "INTU.L", "RGL.L", "DC.L", "0A6E.L", "LRE.L", "WDS.L", "FCH.L", "0R2Q.L", "BLND.L", "RWI.L", 
    "0R2O.L", "WPC.L", "0A6D.L", "WKC.L", "NTR.L", "0A6A.L", "ITV.L", "VOD.L", "MAB.L", "0A6I.L", 
    "NPS.L", "0A6B.L", "AHT.L", "JD.L", "DARK.L", "0A6K.L", "WOSG.L", "AGK.L", "0A6J.L", "TATE.L", 
    "0R2T.L", "SBR.L", "0A6M.L", "WKP.L", "PAG.L", "0A6L.L", "WWH.L", "JDW.L", "0A6P.L", "WDI.L", 
    "BOO.L", "0A6O.L", "TBCG.L", "0A6N.L", "TPK.L", "WG.L", "0A6R.L", "TRN.L", "WEJO.L", "0A6Q.L", 
    "TSCO.L", "0A6U.L", "TIFS.L", "0A6S.L", "TGT.L", "0A6V.L", "SZU.L", "0A6X.L", "SYNT.L", "0A6W.L", 
    "0QAH.L", "0YSU.L", "PHP.L", "QLT.L", "0M8V.L", "SHC.L", "0NC5.L", "EMG.L", "PNN.L", "0QYJ.L", 
    "PLUS.L", "HOC.L", "VMUK.L", "0AI3.L", "HFG.L", "GKN.L", "EOT.L", "0AIE.L", "HAS.L", "0J2C.L", 
    "FGT.L", "BNS.L", "0QZL.L", "FDM.L", "0L0R.L", "FPE.L", "AALB.L", "0AJO.L", "EYE.L", "0YQJ.L", 
    "FDSA.L", "EQQQ.L", "PPD.L", "0H41.L", "EPIC.L", "0D71.L", "ENOG.L", "BBGI.L", "0QZN.L", "EMH.L", 
    "BLME.L", "0TUP.L", "ELM.L", "BBOX.L", "0QLA.L", "ELTA.L", "BBRC.L", "0P67.L", "DWX.L", "BCG.L", 
    "0P8K.L", "DSA.L", "BCAST.L", "0AJP.L", "DRTY.L", "BBY.L", "0ALF.L", "DRGO.L", "BCPT.L", "0QYP.L", 
    "DQ.L", "BEZ.L", "0F0Y.L", "DPP.L", "BGEO.L", "0D7T.L", "DP6C.L", "BGFD.L", "0R28.L", "DPL.L", 
    "BGI.L", "0YQM.L", "DOW.L", "BHMG.L", "0R0L.L", "DOV.L", "BHPG.L", "0YQQ.L", "DOM.L", "BIPS.L", 
    "0YQV.L", "DMGT.L", "BIRD.L", "0K5R.L", "DNLM.L", "0OQR.L", "DKL.L", "BKY.L", "0N7N.L", "DKFS.L", 
    "BLT.L", "0YQW.L", "DIS.L", "BMC.L", "0OQO.L", "DFC.L", "BOWL.L", "0QN1.L", "DEV.L", "BRBY.L", 
    "0QZE.L", "DESG.L", "BUR.L", "AWE.L", "FCSS.L", "0VQD.L", "0L5N.L", "LWDB.L", "0Y3K.L", "SVS.L", 
    "ROSE.L", "CTY.L", "THRL.L", "THRG.L", "MIG3.L", "BRK-B", "0V62.L", "0AJZ.L", "MIG2.L", "49QU.L", 
    "29QU.L", "19QU.L", "0N1W.L", "0AI1.L"
]

def get_uk_tickers():
    return UK_350_TICKERS
