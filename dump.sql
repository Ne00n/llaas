SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

CREATE TABLE `requests` (
  `ID` int(11) NOT NULL,
  `subnet` varchar(20) NOT NULL,
  `ip` varchar(15) NOT NULL,
  `expiry` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `results` (
  `subnet` varchar(20) NOT NULL,
  `worker` varchar(15) NOT NULL,
  `latency` decimal(6,2) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


ALTER TABLE `requests`
  ADD PRIMARY KEY (`ID`),
  ADD UNIQUE KEY `subnet` (`subnet`);

ALTER TABLE `results`
  ADD KEY `subnet` (`subnet`,`worker`);


ALTER TABLE `requests`
  MODIFY `ID` int(11) NOT NULL AUTO_INCREMENT;


ALTER TABLE `results`
  ADD CONSTRAINT `resultsSubnet` FOREIGN KEY (`subnet`) REFERENCES `requests` (`subnet`) ON DELETE CASCADE ON UPDATE CASCADE;
COMMIT;
