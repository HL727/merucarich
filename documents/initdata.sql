-- MySQL dump 10.13  Distrib 5.7.30, for Linux (x86_64)
--
-- Host: 127.0.0.1    Database: richs
-- ------------------------------------------------------
-- Server version	5.5.5-10.1.40-MariaDB-1~bionic

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `accounts_bannedkeyword`
--

DROP TABLE IF EXISTS `accounts_bannedkeyword`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `accounts_bannedkeyword` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `banned_keyword` varchar(100) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=925 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts_bannedkeyword`
--

LOCK TABLES `accounts_bannedkeyword` WRITE;
/*!40000 ALTER TABLE `accounts_bannedkeyword` DISABLE KEYS */;
INSERT INTO `accounts_bannedkeyword` VALUES (743,'Louboutin'),(744,'ルブタン'),(745,'ヴィトン'),(746,'Vuitton'),(747,'Ferragamo'),(748,'フェラガモ'),(749,'GOYARD'),(750,'ゴヤール'),(751,'CHANEL'),(752,'シャネル'),(753,'BALENCIAGA'),(754,'バレンシアガ'),(755,'TATRAS'),(756,'タトラス'),(757,'ジェラートピケ'),(758,'YEEZY'),(759,'エンヴォイ'),(760,'カルティエ'),(761,'Cartier'),(762,'ロレックス'),(763,'ROLEX'),(764,'タミフル'),(765,'Tamiflu'),(766,'エルメス'),(767,'HERMES'),(768,'リーバイス'),(769,'Levi\'s'),(770,'マイケル・コース'),(771,'MICHAEL KORS'),(772,'North Face'),(773,'ノース・フェイス'),(774,'ノースフェイス'),(775,'コーチ'),(776,'Coach'),(777,'バイアグラ'),(778,'Viagra'),(779,'サムスン'),(780,'Samsung'),(781,'ラルフ・ローレン'),(782,'Ralph Lauren'),(783,'BVLGARI'),(784,'ブルガリ'),(785,'ジミーチュウ'),(786,'JIMMY CHOO'),(787,'ヴェルサーチ'),(788,'ベルサーチ'),(789,'VERSACE'),(790,'プラダ'),(791,'PRADA'),(792,'UGG'),(793,'マーク・ジェイコブス'),(794,'Marc Jacobs'),(795,'ティファニー'),(796,'サマンサタバサ'),(797,'Tiffany'),(798,'バーバリー'),(799,'BURBERRY'),(800,'スーパーマッチ'),(801,'supermatch'),(802,'クロムハーツ'),(803,'CHROME HEARTS'),(804,'サンローラン'),(805,'SAINT LAURENT'),(806,'ディオール'),(807,'Dior'),(808,'Champion'),(809,'ヴェイパーマックス'),(810,'A BATHING APE'),(811,'Abercrombie & Fitch'),(812,'adidas'),(813,'BOTTEGA VENETA'),(814,'CALVIN KLEIN'),(815,'CANADA GOOSE'),(816,'CHAN LUU'),(817,'Chloe'),(818,'Christian Louboutin'),(819,'Daniel Wellington'),(820,'Dunhill'),(821,'Ed Hardy'),(822,'emu'),(823,'FENDI'),(824,'FJALL RAVEN'),(825,'Giorgio Armani'),(826,'GUESSS'),(827,'HUNTER'),(828,'IL BISONTE'),(829,'LeSportsac'),(830,'LONGCHAMP'),(831,'LOUIS VUITTON'),(832,'MARC BY MARC JACOBS'),(833,'Mila schon'),(834,'MINNETONKA'),(835,'MONCLER'),(836,'NEW BALANCE'),(837,'NIKE'),(838,'Orobianco'),(839,'PANERAI'),(840,'Paul Smith'),(841,'Polo Ralph Lauren'),(842,'RAY-BAN'),(843,'Salvatore Ferragamo'),(844,'TOD’S'),(845,'TOMS SHOES'),(846,'Vivienne Westwood'),(847,'VANS'),(848,'ア・ベイシング・エイプ'),(849,'アバクロンビー&フィッチ'),(850,'アディダス'),(851,'ボッテガ・ヴェネタ'),(852,'カルバンクライン'),(853,'カナダグース'),(854,'チャン・ルー'),(855,'クロエ'),(856,'クリスチャン・ルブタン'),(857,'ダニエル・ウェリントン'),(858,'ダンヒル'),(859,'エド・ハーディ'),(860,'フェンディ'),(861,'フェールラーベン'),(862,'ジョルジオ・アルマーニ'),(863,'イル・ビソンテ'),(864,'レスポートサック'),(865,'ロンシャン'),(866,'ルイ・ヴィトン'),(867,'ミラ・ショーン'),(868,'ミネトンカ'),(869,'モンクレール'),(870,'ニューバランス'),(871,'ナイキ'),(872,'オロビアンコ'),(873,'パネライ'),(874,'ポール・スミス'),(875,'ポロ・ラルフローレン'),(876,'サルヴァトーレ・フェラガモ'),(877,'トッズ'),(878,'トムス・シューズ'),(879,'トリー・バーチ'),(880,'ヴィヴィアン・ウエストウッド'),(881,'バンズ'),(882,'Go Pro'),(883,'Ergobaby'),(884,'Hoppetta'),(885,'エルゴベビー'),(886,'ホッペッタ'),(887,'Coleman'),(888,'コールマン'),(889,'M·A·C'),(890,'フィリップリム'),(891,'Phillip Lim'),(892,'ジバンシィ'),(893,'GIVENCHY'),(894,'ステラ・マッカートニー'),(895,'STELLA McCARTNEY'),(896,'セリーヌ'),(897,'CELINE'),(898,'トリーバーチ'),(899,'TORY BURCH'),(900,'ドルチェ&ガッバーナ'),(901,'ドルガバ'),(902,'DOLCE&GABBANA'),(903,'バルマン'),(904,'BALMAIN'),(905,'マノロ・ブラニク'),(906,'Manolo Blahnik'),(907,'メゾン・マルジェラ'),(908,'マルジェラ'),(909,'Maison Margiela'),(910,'Margiela'),(911,'ランバン'),(912,'LANVIN'),(913,'ロエベ'),(914,'LOEWE'),(915,'ヴァレクストラ'),(916,'Valextra'),(917,'ヴァレンティノ'),(918,'VALENTINO'),(919,'ヴェトモン'),(920,'VETEMENTS'),(921,'like'),(924,'L\'Arc〜en〜Ciel');
/*!40000 ALTER TABLE `accounts_bannedkeyword` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `mercari_exclude_seller_master`
--

DROP TABLE IF EXISTS `mercari_exclude_seller_master`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `mercari_exclude_seller_master` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `seller_id` varchar(128) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `mercari_exclude_seller_master`
--

LOCK TABLES `mercari_exclude_seller_master` WRITE;
/*!40000 ALTER TABLE `mercari_exclude_seller_master` DISABLE KEYS */;
INSERT INTO `mercari_exclude_seller_master` VALUES (1,'new test'),(2,'MERCARI_MASTER'),(3,'IMPORT_TEST_MERCARI'),(4,'YYY_IMPORT');
/*!40000 ALTER TABLE `mercari_exclude_seller_master` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `yahoo_exclude_seller_master`
--

DROP TABLE IF EXISTS `yahoo_exclude_seller_master`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `yahoo_exclude_seller_master` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `seller_id` varchar(128) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `yahoo_exclude_seller_master_seller_id_1dd96379` (`seller_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `yahoo_exclude_seller_master`
--

LOCK TABLES `yahoo_exclude_seller_master` WRITE;
/*!40000 ALTER TABLE `yahoo_exclude_seller_master` DISABLE KEYS */;
INSERT INTO `yahoo_exclude_seller_master` VALUES (3,'IMPORT_TEST_YAHOO'),(1,'new test'),(4,'XXX_IMPORT'),(2,'YAHOO_MASTER');
/*!40000 ALTER TABLE `yahoo_exclude_seller_master` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `amazon_exclude_asin_master`
--

DROP TABLE IF EXISTS `amazon_exclude_asin_master`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `amazon_exclude_asin_master` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `asin` varchar(16) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `amazon_exclude_asin_master`
--

LOCK TABLES `amazon_exclude_asin_master` WRITE;
/*!40000 ALTER TABLE `amazon_exclude_asin_master` DISABLE KEYS */;
INSERT INTO `amazon_exclude_asin_master` VALUES (1,'XXXYYYZZZ'),(2,'hoge'),(3,'IMPORT_TEST'),(4,'test00001'),(5,'let be know');
/*!40000 ALTER TABLE `amazon_exclude_asin_master` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `amazon_csv_format`
--

DROP TABLE IF EXISTS `amazon_csv_format`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `amazon_csv_format` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `format` varchar(64) NOT NULL,
  `fields` int(11) NOT NULL,
  `feed_product_type` int(11) NOT NULL,
  `item_sku` int(11) NOT NULL,
  `brand_name` int(11) NOT NULL,
  `item_name` int(11) NOT NULL,
  `external_product_id` int(11) NOT NULL,
  `external_product_id_type` int(11) NOT NULL,
  `manufacturer` int(11) NOT NULL,
  `recommended_browse_nodes` int(11) NOT NULL,
  `quantity` int(11) NOT NULL,
  `standard_price` int(11) NOT NULL,
  `main_image_url` int(11) NOT NULL,
  `part_number` int(11) NOT NULL,
  `condition_type` int(11) NOT NULL,
  `condition_note` int(11) NOT NULL,
  `product_description` int(11) NOT NULL,
  `bullet_point` int(11) NOT NULL,
  `generic_keywords` int(11) NOT NULL,
  `other_image_url1` int(11) NOT NULL,
  `other_image_url2` int(11) NOT NULL,
  `other_image_url3` int(11) NOT NULL,
  `fulfillment_latency` int(11) NOT NULL,
  `standard_price_points` int(11) NOT NULL,
  `created_date` datetime(6) NOT NULL,
  `updated_date` datetime(6) NOT NULL,
  `is_adult_product` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `amazon_csv_format_format_bc2a5f27` (`format`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `amazon_csv_format`
--

LOCK TABLES `amazon_csv_format` WRITE;
/*!40000 ALTER TABLE `amazon_csv_format` DISABLE KEYS */;
INSERT INTO `amazon_csv_format` VALUES (1,'Toys',191,0,1,2,3,4,5,6,7,8,9,10,25,166,167,26,-1,36,12,13,14,164,176,'2019-01-05 16:22:47.180933','2019-01-05 16:22:47.180965',85);
/*!40000 ALTER TABLE `amazon_csv_format` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `amazon_parent_category`
--

DROP TABLE IF EXISTS `amazon_parent_category`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `amazon_parent_category` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `display_order` int(11) NOT NULL,
  `name` varchar(256) NOT NULL,
  `value` varchar(256) NOT NULL,
  `created_date` datetime(6) NOT NULL,
  `updated_date` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `amazon_parent_category_display_order_6833bb6d` (`display_order`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `amazon_parent_category`
--

LOCK TABLES `amazon_parent_category` WRITE;
/*!40000 ALTER TABLE `amazon_parent_category` DISABLE KEYS */;
INSERT INTO `amazon_parent_category` VALUES (1,1,'ホビー','Hobbies','2019-01-05 16:19:37.238890','2019-01-05 16:19:37.238945');
/*!40000 ALTER TABLE `amazon_parent_category` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `amazon_hobbies_category`
--

DROP TABLE IF EXISTS `amazon_hobbies_category`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `amazon_hobbies_category` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `display_order` int(11) NOT NULL,
  `name` varchar(256) NOT NULL,
  `format` varchar(64) NOT NULL,
  `feed_product_type` varchar(64) NOT NULL,
  `value` varchar(64) NOT NULL,
  `created_date` datetime(6) NOT NULL,
  `updated_date` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `amazon_hobbies_category_display_order_6763f53b` (`display_order`),
  KEY `amazon_hobbies_category_value_a8815837` (`value`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `amazon_hobbies_category`
--

LOCK TABLES `amazon_hobbies_category` WRITE;
/*!40000 ALTER TABLE `amazon_hobbies_category` DISABLE KEYS */;
INSERT INTO `amazon_hobbies_category` VALUES (1,1,'ホビー（その他）','Toys','Hobbies','2277722051','2019-01-05 16:20:54.689004','2019-01-05 16:20:54.689049');
/*!40000 ALTER TABLE `amazon_hobbies_category` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2020-07-21  0:25:19
