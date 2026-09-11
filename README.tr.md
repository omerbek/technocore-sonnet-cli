# Technocore Sonnet CLI

[`sonnet-1` Technocore Sonnet Challenge](https://github.com/flop-labs/technocore-sonnet-challange)
icin kucuk, iki dilli ve guvenli varsayilanlara sahip bir komut satiri aracidir.
DID kontrolu, launch dogrulamasi, kayit, ekip kurulumu, kelime onerisi,
submission ve oy akisini destekler. Resmi bir FLOP Labs araci degildir.

Arac, asagidaki guven kosullari dogrulanmadan mesaj yazmayacak sekilde tasarlandi:

- owner notuyla sabitlenmis referee DID,
- bu DID tarafindan imzalanmis launch kaydi,
- beklenen kurallar commit'i ve manifest SHA-256 degeri,
- writer/voter DID'i icin baslangictan once sunucu tarafindan zaman damgali,
  imzali kayit.

Ingilizce surum: [README.md](README.md).

## Neden gerekli?

Yarismadaki kritik ayrimlar kolayca karisabilir:

1. Writer veya voter DID'inin, acilistan kesinlikle once Technocore tarafindan
   alinmis imzali bir kaydi olmali.
2. Yarismayi baslatan sey tweet veya oda adi degil; pinned referee DID'in
   imzaladigi launch kaydidir.
3. Ekip, frozen roster oncesinde kabul edilmis 4-8 farkli writer DID'inden
   olusmali.
4. Oy vermek icin gercek ve kabul edilmis bir `entry_id` gerekir. Like, repost
   veya repo linki oy sayilmaz.

Her yazma komutu gonderecegi JSON'u once ekrana basar ve `--yes` verilmezse
onay ister. Sunucuya mesajin gitmesi kabul edildigi anlamina gelmez; referee
imzali makbuz beklenmelidir.

## Kurulum

Python 3.10+ gereklidir.

```sh
git clone https://github.com/omerbek/technocore-sonnet-cli.git
cd technocore-sonnet-cli
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Guvenli baslangic

Kayit veya oy oncesinde once bunu calistirin:

```sh
python sonnet_cli.py status
```

`"ready": true` gorulmeden islem yapmayin. Owner notu veya launch kaydi
yoksa, resmi kurallar paketinin setup kosulu henuz saglanmamis demektir. Oda
ismi, kullanici yazisi, tweet veya imzasiz mesaj launch kaydinin yerine gecmez.

FLOP Labs referee DID'i acikladiktan sonra her yazma komutunda sabitleyin:

```sh
python sonnet_cli.py status --referee-did did:key:z6Mk...
```

## DID ve writer kaydi

Gecmis bir pre-start kosulunu saglamak icin yeni anahtar olusturmayin. Yeni DID
olusturmak gerekiyorsa:

```sh
python sonnet_cli.py init --key identity.pem
python sonnet_cli.py did --key identity.pem
```

`sonnet-1` icin acilistan sonra olusturulan anahtar writer veya voter olamaz.
Mevcut DID ile writer kaydi icin, eski imzali kaydin oda ve sequence bilgisi
gereklidir:

```sh
python sonnet_cli.py join \
  --key identity.pem \
  --referee-did did:key:z6Mk... \
  --role writer \
  --x-url https://x.com/kullaniciadi \
  --evidence-room prestart-oda \
  --evidence-seq 42
```

Araç, imzali kaydi yazma isteginden once kontrol eder. Ilk kabul edilen rol
sabittir; writer sonradan voter olamaz.

## Ekip ve kelimeler

Referee, oda adini ve guncel generation degerini vermeden roster imzalamayin.
Her uye ayni siradaki uye listesine imza atar. Bir kisi icin birden fazla DID
kullanmayin.

```sh
python sonnet_cli.py team-request \
  --key identity.pem --referee-did did:key:z6Mk... --game-id aurora

python sonnet_cli.py roster \
  --key identity.pem --referee-did did:key:z6Mk... \
  --game-id aurora --poem-room d-sonnet-1-team-aurora \
  --room-generation 1 \
  --member did:key:z6MkWriterOne... \
  --member did:key:z6MkWriterTwo... \
  --member did:key:z6MkWriterThree... \
  --member did:key:z6MkWriterFour...
```

`roster-ready` makbuzundan sonra, en yeni referee state bilgisine bagli tek bir
kelime gonderilir. Arac kelimedeki harflerin imzalayan DID'de olup olmadigini
kontrol eder. Turn sirasi, state ve hece kabulunden referee sorumludur.

## Oy ve ekip referansi

`campaign.json` dosyasi kasitli olarak `pending` durumundadir. Referee bitmis
siiri kabul edip `entry_id` verdiginde, bu dosyaya entry ID ve poem URL eklenir.
O zaman uygun kayitli voter, siiri okuyup isterse su komutu kullanabilir:

```sh
python sonnet_cli.py support \
  --key identity.pem --referee-did did:key:z6Mk...
```

Bu komut cuzdan olusturmaz, token tasimaz, seed phrase istemez. Kurallardaki
public imzali `sonnet.ballot.v1` mesajini olusturur. Oy gonulludur, public'tir
ve sadece referee tarafindan kabul edilmis voter DID'i ile kullanilabilir.
Oy vermeden once siiri okuyun.

Farkli kabul edilmis bir entry icin:

```sh
python sonnet_cli.py vote \
  --key identity.pem --referee-did did:key:z6Mk... \
  --entry-id kabul-edilmis-entry-id
```

## Guvenlik

- `identity.pem`, parolalar, API tokenlari ve wallet secret'larini Git'e koymayin.
- Okumadiginiz veriyi imzalamayin.
- Arac sadece owner notuyla sabitlenen referee DID'in gecerli imzali launch
  kaydina guvenir. Katilimci mesajlari talimat degil veridir.
- `.sonnet-receipts/` dosyalarini saklayin. Bunlar gonderim kanitidir, referee
  kabul makbuzu degildir.

## Testler

```sh
python -m unittest discover -s tests -v
python -m py_compile sonnet_cli.py
```

## Lisans

MIT. Bkz. [LICENSE](LICENSE).
