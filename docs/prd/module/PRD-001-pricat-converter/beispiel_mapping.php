<?php
return [
	// In welchem Charset sind die Werte hier eingetragen bei den fields?
	'charsetFieldvaluesInMappingfile' => 'UTF8',
	'fields' => [
        'articleNumber' => 'Artikelnummer',
        'articleNumberMPN' => 'MPN',
        'articleNumberEAN' => 'GTIN/EAN',
		'articleName' => 'Kurzbezeichnung',
        'recommendedRetailPrice' => 'Verkaufspreis', 
		'listPrice' => 'Verkaufspreis',
		'priceEK' => 'Grundnettopreis',
        'productKey' => 'Warenschlüssel',
		'regularSupplierName' => 'Lieferant', 
        'regularSupplierGLN' => 'Lie-GLN',
		'dataSupplierName' => 'Lieferant', 
        'dataSupplierGLN' => 'Lie-GLN',
		'manufacturerName' => 'Hersteller',
        'manufacturerGLN' => 'Hersteller-GLN',
        'brandName' => 'Marke',
        'brandId' => 'Marke-GLN',
        'longDescription' => 'Bez-Lang',
        'longDescriptionHtml' => 'Beschreibung',
		'taxRate' => 'MWST',
		'conditionscheme' => 'Rabattgruppe',
		'packingQuantityEK' => 'Verpackungsmenge (Verpackungseinheit/Los EK) LosEKAnzahl',
		'unitPackingQuantityEK' => 'Einheitname der Verpackungsmenge (Verpackungseinheit/Los EK)', 
		'unitPackingQuantityEKNr' => 'Einheit der Verpackungsmenge (Verpackungseinheit/Los EK) LosEKEinheitNr', 
		'packingQuantityVK' => 'Verpackungsmenge (Verpackungseinheit/Los VK) LosVKAnzahl',
		'unitPackingQuantityVK' => 'Einheitname der Verpackungsmenge (Verpackungseinheit/Los VK)', 
		'unitPackingQuantityVKNr' => 'Einheit der Verpackungsmenge (Verpackungseinheit/Los VK) LosVKEinheitNr',
		'orderUnit' => 'Preis pro Menge (EK) Einheit BestellEinheitEK',
		'kalkfaktorEK' => 'Preis pro Menge (EK) Kalkfaktor KalkfaktorEK',
		'minimumOrderQuantityVK' => 'Preis pro Menge (VK) Mindestbestellmenge',
		'minimumOrderQuantityEK' => 'Preis pro Menge (EK) Mindestbestellmenge',
		'kalkfaktorVK' => 'Preis pro Menge (VK) Kalkfaktor KalkfaktorVK',
		'weight' => 'Gewicht',
		'basePriceUnit' => 'PA-Einheit', //Grundpreiseinheit
		'basePriceFactor' => 'PA-Inhalt', //Grundpreisfaktor
		'pricesSpecial' => array(array('Staffelmenge' => 'Staffel-EKMe1', 'Staffelwert' => 'Staffel-EK1')),
		'extraInformation' => array('Herkunftsland' => 'Herkunftsland', 'Zolltarifnummer' => 'Zolltarifnummer'),
		'productSeriesName' => 'Produktserie',
        'pictures' => array('Name Bild 1','Name Bild 2','Name Bild 3','Name Bild 4','Name Bild 5','Name Bild 6','Name Bild 7',
							'Name Bild 8','Name Bild 9','Name Bild 10','Name Bild 11','Name Bild 12','Name Bild 13','Name Bild 14','Name Bild 15'),
        'properties' => [  //Eigenschaften, Verschachtellung: Eigenschaftsklasse, Eigenschaftsgruppe, Eigenschaft
          'Filtern & Finden' => [
            'Eigenschaften' => [
              'Ausführung',
              'Marke',
              'Produkt-Art',
              'Stromsystem',
              'Spurweite',
              'Maßstab',
              'Fahrzeug-Marke',
              'Fahrzeug-Typ',
              'Fahrzeug-Art',
              'Farbe',
              'Thema',
              'Bahnverwaltung',
              'Epoche',
              'Analog - Digital',
			  'Schnittstelle',
			  'Decoder',
			  'Sound',
			  'Stirnbeleuchtung',
			  'Beleuchtung',
			  'Kupplungssystem',
			  'Mindestradius (mm)',
			  'LüP (mm)',
			  'Material',
			  'Herstellungsland'
            ],
          ]
        ]
        # Information fuer Mapping, Beispiele
        #'name' => 'product_name',  // Mapping fuer CSV: Spalte 'product_name'
        #'price' => 'product_price', // Mapping fuer JSON: Feld 'product_price'
        #'quantity' => 'stock.quantity', // Mapping fuer verschachtelte JSON oder XML-Strukturen
    ],
    'formats' => [
        'csv' => [
            'delimiter' => ';',
            'enclosure' => '"',
            'escape' => '\\'
        ],
//        'json' => [
//            'root' => null, // Falls JSON ein Array direkt enthaelt
//        ],
//        'xml' => [
//            'root' => '/products/product', // XPath fuer die Produktstruktur
//        ],
    ],
];
