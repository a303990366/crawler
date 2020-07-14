### 由於selenium本體是網頁測試工具，所以selenium的程式較為稀少(因為被學長鞭策過 哈哈)

#### 稍微敘述一下該程式，該程式是程式設計課程的期末專題，會發想抓取104網站的原因是台北租屋太貴，又很怕被騙，所以想透過較為系統化的方式將數據可視化。
#### 總共有4個模組。一為將租屋價格進行可視化(製作盒鬚圖);二為計算屋內設備的完善率;三為找出熱門物件;四為找出特定房東出租的物件。
#### 特別講一下第四個模組，該模組是因為104網站沒有像好房網一樣可以搜尋特定刊登者的物件，所以可能面對自己喜歡的物件卻無法找出相似度較高的，因此才產生該模組，該模組是透過前三個模組集大成取出較優的刊登者作為我們要探尋的房東。


### 後記:本來想要順便做好房網的爬蟲，但是時間急迫就沒有額外製作，不過欄位內容是通用的。此外，發現房屋類型相關網站都搞動態載入，讓我覺得好麻煩阿!而且selenium的執行速度較慢，所以讓selenium抓取完物件網址就改成用requests去跑，減少爬取時間。