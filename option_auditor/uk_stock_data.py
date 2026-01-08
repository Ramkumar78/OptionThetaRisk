# UK FTSE 350 Representative List (Yahoo Finance Tickers ending in .L)
UK_TICKERS = [
    "RR.L", "BP.L", "SHEL.L", "HSBA.L", "LLOY.L", "BARC.L", "NWG.L", "VOD.L",
    "BT.A.L", "GSK.L", "AZN.L", "ULVR.L", "DGE.L", "BATS.L", "IMB.L", "RIO.L",
    "GLEN.L", "AAL.L", "ANTO.L", "NG.L", "SSE.L", "CNA.L", "UU.L", "SVT.L",
    "TSCO.L", "SBRY.L", "OCDO.L", "MKS.L", "NXT.L", "JD.L", "ABF.L", "WTB.L",
    "IAG.L", "EZJ.L", "RYA.L", "WIZZ.L", "TUI.L", "IHG.L", "CPG.L", "EXPN.L",
    "REL.L", "WPP.L", "INF.L", "PSON.L", "AUTO.L", "RMV.L", "SPX.L", "WEIR.L",
    "SMIN.L", "GKN.L", "MEL.L", "ROAR.L", "QQ.L", "LSEG.L", "PRU.L", "AV.L",
    "LGEN.L", "PHNX.L", "MNG.L", "SLA.L", "HL.L", "STJ.L", "ADM.L", "DLG.L",
    "RS1.L", "KGF.L", "MNDI.L", "DSUS.L", "SMDS.L", "SKG.L", "CRDA.L", "JMAT.L",
    "VCT.L", "HLMA.L", "AHT.L", "BNZL.L", "DCC.L", "ITRK.L", "SGE.L", "SN.L"
]

UK_EURO_TICKERS = [
    # Top 50 FTSE (UK)
    "AZN.L", "SHEL.L", "HSBA.L", "ULVR.L", "BP.L", "RIO.L", "REL.L", "GSK.L", "DGE.L", "LSEG.L", "BATS.L", "GLEN.L", "BA.L", "CNA.L", "NG.L", "LLOY.L", "RR.L", "BARC.L", "CPG.L", "NWG.L", "RKT.L", "VOD.L", "AAL.L", "SGE.L", "HLN.L", "EXR.L", "TSCO.L", "SSE.L", "MNG.L", "ADM.L", "III.L", "ANTO.L", "SPX.L", "STAN.L", "IMB.L", "WTB.L", "SVT.L", "AUTO.L", "SN.L", "CRDA.L", "WPP.L", "SMIN.L", "DCC.L", "AV.L", "LGEN.L", "KGF.L", "SBRY.L", "MKS.L", "LAND.L", "PSON.L",
    # Liquid UK Mid-Caps
    "JD.L", "IAG.L", "EZJ.L", "AML.L", "IDS.L", "DLG.L", "ITM.L", "QQ.L", "GRG.L", "VTY.L", "BTRW.L", "BOO.L", "ASOS.L", "HBR.L", "ENOG.L", "TLW.L", "CWR.L", "GNC.L", "THG.L", "CURY.L", "DOM.L", "SFOR.L", "PETS.L", "MRO.L", "INVP.L", "OCDO.L", "IGG.L", "CMC.L", "PLUS.L", "EMG.L", "HWDN.L", "COST.L", "BEZ.L", "SGRO.L", "PSN.L", "TW.L", "BYG.L", "SAFE.L", "UTG.L", "BBOX.L", "MANG.L", "TPK.L", "HIK.L", "SRO.L", "FRES.L", "KAP.L", "WKP.L", "JMAT.L", "RS1.L", "PNN.L",
    # Top 50 Euro
    "ASML.AS", "MC.PA", "SAP.DE", "RMS.PA", "TTE.PA", "SIE.DE", "CDI.PA", "AIR.PA", "SAN.MC", "IBE.MC", "OR.PA", "ALV.DE", "SU.PA", "EL.PA", "AI.PA", "BNP.PA", "DTE.DE", "ENEL.MI", "DG.PA", "BBVA.MC", "CS.PA", "BAS.DE", "ADS.DE", "MUV2.DE", "IFX.DE", "SAF.PA", "ENI.MI", "INGA.AS", "ISP.MI", "KER.PA", "STLAP.PA", "AD.AS", "VOW3.DE", "BMW.DE", "MBG.DE", "BAYN.DE", "DB1.DE", "BN.PA", "RI.PA", "CRH.L", "G.MI", "PHIA.AS", "HEIA.AS", "NOKIA.HE", "VIV.PA", "ORA.PA", "KNEBV.HE", "UMG.AS", "HO.PA", "ABI.BR"
]

def get_uk_tickers():
    return UK_TICKERS

def get_uk_euro_tickers():
    """Returns normalized UK/Euro tickers list."""
    return list(set(UK_EURO_TICKERS))
