# BBVA AI Innovation — Türkçe anlatım metni

30 sahne · 45 dakikalık konuşma ve görsel gösterim planı

Ana ekran İngilizcedir. Bu metin konuşmacı içindir; süreler animasyonları, duraklamaları ve canlı hesap gösterimini de kapsar.

## 01. Can one AI change how another AI behaves?
**Süre:** 1:13 · **Görsel adımlar:** Meet the source study → See its central idea → Follow the intervention

Bugün bir yapay zekâ modelini, başka bir modelin sayısal yapısına müdahale eden bir araştırmacı olarak kullanma fikrini anlatacağım. Günlük kullanımda bir dil modelinden metin yazmasını, kod üretmesini veya bir problemi çözmesini istiyoruz. Buradaki görev farklı: elinde çalışan bir sinir ağı var; bu ağın bağlantı katsayılarını incelemesini ve belli bir davranışı değiştirecek sayısal müdahaleler önermesini istiyoruz.

Bizi bu deneye yönelten çalışma, ekranda gördüğünüz “Sparks of Weight-Space Programming”. Rikiya Takehi, Jayden Teoh, Alex Zhang ve Omar Khattab’ın çalışması, dil modellerinin başka ağların ağırlıklarını okuyabilmesini, yazabilmesini ve mevcut ağlarda belirli davranışlara müdahale edebilmesini araştırıyor. Buradaki ağırlık dediğimiz şey, hesaplamada kullanılan kalıcı bir sayısal katsayı. Birazdan bir katsayının bir tahmini nasıl etkilediğini birlikte hesaplayacağız.

Önce bu kaynak çalışmanın gerçekten ne yaptığını iki örnek üzerinden açacağım. Sonra bizim gelir sınıflandırıcısı ve küçük dil modeli üzerinde hangi soruları sorduğumuzu, editörlere ne verdiğimizi ve sonuçta hangi kararların değiştiğini izleyeceğiz. Anlatının sonundaki sayılar, bu işlemlerin ölçülmüş sonuçları olacak.

## 02. Astra used the task to design a weight change.
**Süre:** 1:13 · **Görsel adımlar:** Define the target behavior → Inspect the numerical network → Write an intervention → Run the modified network

Kaynak çalışmada iki farklı rol var. Editör rolünde GPT-6 Astra bulunuyor. Diğer tarafta ise değiştirilecek hedef sinir ağı var. Editör, hedef ağın yapısını ve sayısal parametrelerini görev tanımıyla birlikte ele alıyor. Bazı deneylerde bütün küçük ağın katsayıları doğrudan metin olarak veriliyor; daha büyük hedeflerde parametreleri ve davranışları incelemek için araçlar kullanılıyor.

İşin özü şu bağlantı: hedeflenen davranış nedir, mevcut ağ bunu nasıl hesaplıyor ve hangi sayısal değişiklik bu hesaplamayı etkileyebilir? Astra bir müdahale öneriyor. Daha sonra bu müdahale hedef ağa uygulanıyor ve davranış ölçülüyor. Dolayısıyla önerinin ikna edici görünmesiyle, uygulandıktan sonra işe yaraması ayrı aşamalar.

Çalışmanın farklı deneyleri aynı yeteneğin farklı yüzlerini araştırıyor. Bazılarında ağırlıklardan ağın ne yaptığını çıkarmak, bazılarında sıfırdan bir ağ yazmak, bazılarında ise başarısız bir davranışı değiştirmek amaçlanıyor. Bizim çalışmamız açısından özellikle iki örnek önemli: bir arabanın kontrolünü değiştirmek ve matematik çözen bir dil modelinin tekrar davranışına müdahale etmek. Şimdi önce hareketin çok açık görülebildiği araba örneğine bakalım.

## 03. A stalled car gets a run-up.
**Süre:** 1:42 · **Görsel adımlar:** Watch the original behavior → See the control rule → Apply the revised behavior → Read the measured outcome

Bu görevde küçük bir araç rampadan geçerek kırmızı bölgenin ötesindeki mavi hedefe ulaşmaya çalışıyor. Kaynak çalışmanın eğitilmiş kontrol ağı rampaya geliyor fakat orada takılıyor. Bir hareket komutunun kendi başına doğru görünmesi yeterli olmuyor; hareketlerin sırası ve aracın taşıdığı momentum belirleyici.

Astra’ya görevin kuralları, ağın yapısı, ağırlıkları ve başarısız davranışın bir örneği veriliyor. Önerdiği müdahale, konum ve hız bilgisini kullanan küçük bir kontrol yolu. Ekranda önce araç geri açılıyor. Bu, hızlanmak için mesafe yaratıyor. Ardından rampaya doğru güçlü biçimde ilerliyor. Belirlenen konumu geçince eklenen yolun etkisi azalıyor ve mevcut politika kalan hareketi sürdürüyor.

Burada animasyonun anlattığı şey, ağın içine bir davranış sırasının sayılarla yerleştirilmesi. Kaynak deneyde 171.664 aktör parametresinin 6.073’ü değişmiş. Değiştirilen politika, ayrı değerlendirmedeki 1.024 denemenin tamamında hedefe ulaşmış. Bu başarı, bu belirli görev ve bu düzenlenmiş politika için raporlanıyor.

Bizim için çıkarılacak fikir şu: dil modeli, görevin anlamını kullanarak bir kontrol davranışı tasarlıyor ve bunu ağırlık müdahalesine çeviriyor. Şimdi hareket komutları yerine dil üretimini etkileyen ikinci örneğe geçelim.

## 04. A math model kept circling back.
**Süre:** 1:13 · **Görsel adımlar:** A problem enters the model → Repetition consumes the answer → Astra compares internal responses

İkinci örnekte hedef Qwen3.5-0.8B. Modelden matematik problemlerini adım adım çözmesi ve sonunda bir cevap üretmesi isteniyor. Ancak modelin üretiminde belirgin bir tekrar sorunu var. Akıl yürütme ilerlemek yerine daha önceki içeriğe dönüyor; çıktı uzuyor ve model sıklıkla izin verilen uzunluğun sonuna geliyor.

Ekrandaki döngü, bu davranışın kavramsal gösterimi. Kaynak deneyin ilk tanılama grubunda 96 yanıtın 85’i 32.768 token sınırına ulaşmış. Yani toplam çıktı bütçesinin büyük bir kısmı, yararlı bir sonuca ilerlemeyen üretimde tüketiliyor. Bu, yalnızca final cevap doğru mu sorusuna bakıldığında gözden kaçabilecek bir davranış sorunu.

Astra önce bu başarısızlığı tanımlıyor. Ardından üretken biçimde ilerleyen bağlamlarla tekrara giren bağlamların model içindeki temsillerini karşılaştırıyor. Böylece hangi iç katkıların tekrar davranışıyla ilişkili olduğunu araştırıyor. Modelin ağırlıklarını değiştirmeden önce, değiştirmek istediği mekanizma hakkında ölçülebilir bir hipotez kurmuş oluyor.

Sonraki sahnede bu hipotezin nasıl somut bir matematiksel işleme dönüştüğünü göreceğiz. Özellikle ekranda ortaya çıkacak “6” sayısının neyi temsil ettiğini açıkça ayıracağız.

## 05. Reduce the contribution that drives repetition.
**Süre:** 1:57 · **Görsel adımlar:** Find the direction → Select the writers → Set the intervention strength → Apply the chosen change

Burada üç aşama var. İlkinde Astra, ilerleyen ve tekrara giren bağlamlardan elde edilen model içi yanıtları karşılaştırıyor. Bu karşılaştırmadan tekrar davranışıyla ilişkili bir yön çıkarıyor. Yönü, iç temsil uzayında belirli bir tür katkıyı tarif eden ok gibi düşünebiliriz.

İkinci aşamada, bu yöndeki katkıyı güçlü biçimde yazan MLP çıkış sütunlarını seçiyor. Son müdahale, 15 ve 19 numaralı katmanların her birinde 64 sütunu hedefliyor. Yani bütün model aynı biçimde ölçeklenmiyor; iki belirli yerde, seçilmiş sütunlar üzerinde çalışılıyor.

Üçüncü aşama müdahalenin büyüklüğü. Ekrandaki 6 bir katman veya nöron sayısı değil; tekrar yönündeki düzeltmenin çarpanı. Kaynak çalışma farklı müdahale şiddetlerini ve katman seçeneklerini ölçmüş; kaydedilen son düzenleme bu çarpanı 6 olarak kullanmış. Formülde önce bir ağırlık sütununun u yönündeki katkısı hesaplanıyor. Bunun altı katı aynı yönde geri çıkarılıyor. Bu büyüklük, kaynaktaki arama ve değerlendirme sürecinin seçtiği ayar.

İşlem iki matris boyunca 131.072 değeri hedefliyor. Yuvarlama sonrasında gerçekten farklı kalan değer sayısı kaynak kaydında ayrıca tutulmuş. Anlatıdaki temel nokta, teşhis edilen davranışla matematiksel müdahalenin birbirine bağlanması. Şimdi bunun dışarıdan gözlenen sonucu ne olmuş, ona bakalım.

## 06. More answers reached a useful conclusion.
**Süre:** 1:13 · **Görsel adımlar:** Compare correct answers → Compare truncated answers → Connect intervention to behavior

Kaynak çalışmanın MATH-500 değerlendirmesinde doğruluk yüzde 7,9’dan yüzde 48,1’e yükselmiş. MATH-500, beş yüz matematik sorusundan oluşan değerlendirme kümesi; burada raporlanan oran, soru başına birden fazla örneklenmiş üretimin ortalaması. Ekrandaki yüzdelik göstergeler bu toplu ölçümü temsil ediyor.

Aynı anda ikinci bir ölçüme bakıyoruz: yanıtların token sınırına ulaşma oranı yüzde 93’ten yüzde 33,1’e düşüyor. Bu iki değişimi birlikte görmek, müdahalenin neden ilginç olduğunu açıklıyor. Model daha sık bir sonuca ulaşabiliyor ve tamamlanan üretimler içinde doğru matematik cevapları da artıyor.

Kaynağın yaptığı mekanizma incelemeleri ve kontrol denemeleri, bu kazanımı tekrar davranışına yapılan hedefli müdahaleyle ilişkilendiriyor. Burada gözümüzün önündeki zincir şu: başarısız davranışı gözle, iç katkıyı ölç, ilgili sütunları değiştir, son davranışı yeniden değerlendir.

Biz de bu fikirden hareket ettik. Fakat kendi deneyimizde görevleri ve müdahale alanını değiştirdik. Küçük bir tablo modeli ile başka bir küçük dil modelini seçtik ve bir de iki editörün birlikte çalışmasını ekledik. Şimdi bizim araştırma sorularımızı net biçimde koyalım.

## 07. Three questions shaped our experiment.
**Süre:** 1:28 · **Görsel adımlar:** Question 1 · classification → Question 2 · language → Question 3 · collaboration

Birinci sorumuz gelir sınıflandırıcısıyla ilgiliydi. Önce eğittiğimiz küçük ağın belirli bağlantılarını kapattık. Daha sonra GPT modellerinden kalan bağlantı katsayılarını düzenlemelerini istedik. Ölçmek istediğimiz şey, bu doğrudan düzenlemelerin sınıfları eşit ağırlıklandıran doğruluk ölçüsünü geliştirip geliştirebildiğiydi.

İkinci sorumuz, zaten eğitilmiş küçük bir dil modeliyle ilgiliydi. SmolLM2-1.7B’nin belirli MLP çıkış ağırlıklarında küçük değişiklikler yapıldığında çoktan seçmeli sorulardaki cevap seçimi iyileşiyor mu? Bu hedef, kaynak çalışmadaki tekrar problemi etrafında kurulmuş müdahaleden farklı: burada doğrudan benchmark başarısını artıracak bir düzenleme aranıyor.

Üçüncü sorumuz işbirliğiydi. GPT-6.1 Sol ve GPT-6 Astra bağımsız olarak çalıştıktan sonra, önceki denemelerin geri bildirimlerini paylaşarak birlikte çalıştıklarında nasıl bir sonuç ortaya çıkıyor? Ortak çalışmanın seçtiği son modeli, bağımsız seçilmiş modellerle karşılaştırıyoruz.

Bu üç soru sunum boyunca RQ1, RQ2 ve RQ3 olarak karşımıza çıkacak. Her sonuç bölümünde ilgili sorunun cevabına döneceğiz. Böylece yalnız hangi skoru aldığımızı değil, o skoru neden ölçtüğümüzü de baştan biliyoruz.

## 08. Two targets. Four selected models.
**Süre:** 1:13 · **Görsel adımlar:** Start with the two targets → Run independent editing → Add the joint session → Compare the selected models

İki hedefin başlangıcı farklı. Census gelir modelini biz eğittik ve ardından belirli bağlantılarını sıfırladık. SmolLM2 ise kamuya açık, önceden eğitilmiş bir dil modeli olarak alındı. Her hedef için ortak nokta, düzenleme koşullarının aynı başlangıç ağırlıklarından hareket etmesi.

Sol ve Astra ilk aşamada bağımsız çalışıyor. Her biri verilen tanılama bilgisine bakıyor, izinli ağırlıklara bir yama öneriyor ve bu yamanın geliştirme puanını alıyor. Adaylar arasından seçilen bir son model oluşuyor. Ardından ortak çalışma, bu bağımsız denemelerin kayıtlarını bilgi olarak kullanıyor. Kendi adaylarını yine aynı başlangıç ağırlıklarına göre üretiyor.

Sonunda karşılaştırma masasında dört isim var: başlangıç modeli, Sol’un seçimi, Astra’nın seçimi ve ortak çalışmanın seçimi. Bu isimler hedef modelin farklı seçilmiş durumlarını ifade ediyor; GPT modellerinin kendilerinin benchmark sorularını yanıtlamasını ölçmüyoruz.

Bu düzen, hem model değişikliğini hem de çalışma biçimini görünür kılıyor. Aşağıdaki bütün sonuçlarda sorumuz, editörün önerdiği yama uygulandıktan sonra hedef modelin ne yaptığı. Şimdi birinci hedefin verisini ve eğitilmiş ağını yakından görelim.

## 09. A table of people and an income label.
**Süre:** 1:28 · **Görsel adımlar:** Open the feature columns → Read one illustrative record → Reveal the target label

Birinci görev UCI Adult, diğer adıyla Census Income veri seti üzerinde gelir sınıflandırması. Her satır bir kaydı, her kolon o kaydın bir özelliğini temsil ediyor. Yaş, eğitim düzeyi, meslek ve haftalık çalışma saati gibi alanlar var. Tahmin etmek istediğimiz etiket, yıllık gelirin 50.000 doların üzerinde olup olmadığı.

Tablo açıldığında önce kolonların görevini görelim. Yaş sayısal bir alan. Eğitim ve meslek kategorik alanlar. Haftalık çalışma saati tekrar sayısal. Son kolondaki gelir sınıfı ise modele öğretmek ve daha sonra tahminini kontrol etmek için kullanılan hedef. Ekrandaki satırlar görevi açıklayan örnekler; birazdan göstereceğimiz final kararları ayrıca kaydedilmiş gerçek model çıktıları olacak.

Veri setinde toplam 48.842 kayıt ve 14 özgün özellik alanı bulunuyor. Bu çalışmadaki kodlama, cinsiyet ve ırk alanlarını tahmin girdilerinin dışında tutuyor. Kategorik alanlar sayısal göstergelere açıldığında ağın kullandığı giriş boyutu 104 oluyor.

Bu görevi seçmemizin pratik değeri, girişten karara kadar bütün hesabı küçük bir ağ üzerinde açabilmemiz. Böylece yalnız final skoru değil, gerçekten hangi bağlantının değiştiğini de gösterebiliyoruz.

## 10. We trained the network, then opened an editing stage.
**Süre:** 1:28 · **Görsel adımlar:** Separate training and final test → Build the initial classifier → Prepare editing feedback

Veri, deneyde farklı görevler üstleniyor. Özgün eğitim kaynağında 32.561, son test bölümünde 16.281 kayıt var. Eğitim kaynağının 22.792 kaydıyla ilk sinir ağını eğittik. Kodlama dönüşümleri de bu öğrenme bölümüne göre oluşturuldu.

Başlangıç ağımız 104 sayısal giriş alıyor. Ardından 32 nöronlu bir ReLU katmanı, 16 nöronlu ikinci bir ReLU katmanı ve tek sigmoid çıktı geliyor. İlk eğitim Adam ile yapılmış. Bu aşamada model, veriden bağlantı katsayılarını öğreniyor. Daha sonraki deney, artık bu öğrenilmiş katsayılar üzerinde çalışan bir düzenleme aşaması.

Eğitim kaynağının diğer bölümlerinde 3.256 kayıt lezyonun etkisini değerlendirmek, 6.513 kayıt ise düzenleme panellerini oluşturmak için ayrılmış. Editörün inceleyebildiği tanılama paneli 256 kayıt; adaylarının karşılaştırıldığı geliştirme paneli 2.048 kayıt. En sonda seçilmiş modeller 16.281 test kaydında değerlendiriliyor.

Buradaki akışın önemi, her sayının belirli bir işe bağlanması. Önce modelin katsayıları öğreniliyor. Sonra editör adayları karşılaştırılıyor. Son olarak seçilmiş modellerin davranışı aynı test kayıtları üzerinde ölçülüyor. Şimdi bu ağdaki bir bağlantının tam olarak ne yaptığını canlı bir hesap üzerinden açalım.

## 11. A weight multiplies a signal.
**Süre:** 1:57 · **Görsel adımlar:** Multiply the two inputs → Add the contributions → Convert the output to probability → Change the first weight

Bu küçük hesap örneği, bir ağırlığın etkisini görünür kılmak için kurulmuş. İki girişimiz var: 2 ve 1. İlk bağlantının ağırlığı 0,4; ikinci bağlantının ağırlığı eksi 0,3. İlk çarpım 0,8, ikinci çarpım eksi 0,3 oluyor. Bunları ve 0,1 sabit terimini topladığımızda 0,6 elde ediyoruz.

ReLU, pozitif 0,6 değerini sonraki aşamaya geçiriyor. Çıkış hesabında bu değer 1,2 ile çarpılıp 0,4 çıkarılıyor; sonuç 0,32. Sigmoid, bu sayıyı yaklaşık yüzde 57,93 olasılığa çeviriyor. Karar eşiğimiz yüzde 50 ise bu örnek üst sınıfa atanıyor.

Şimdi yalnız ilk ağırlığı 0,4’ten 0,2’ye alıyorum. Aynı girdiler tekrar hesaplanıyor. İlk katkı 0,4’e, ara aktivasyon 0,2’ye düşüyor. Çıkış olasılığı yaklaşık yüzde 46,01 oluyor ve karar diğer sınıfa geçiyor. Ekrandaki bütün sayılar aynı hesap zincirine bağlı.

Burada sürgüyü küçük miktarda da oynatabiliriz. Olasılık değişebilir ama eşik aşılmadığı sürece sınıf aynı kalabilir. Bir ağırlık müdahalesinin etkisini değerlendirmek için hem sayısal çıktıya hem de son karar kuralına bakmamızın nedeni bu.

## 12. We set 16 connection columns to zero.
**Süre:** 1:28 · **Görsel adımlar:** Open the second layer → Apply the permanent mask → Inspect the editing region

Şimdi gerçek modelimizde hangi bölgeye müdahale ettiğimizi görüyoruz. İkinci katmanın ağırlık matrisi 16 satır ve 32 sütundan oluşuyor. Bir satır, ikinci katmandaki bir hedef nörona gelen bağlantıları; bir sütun ise önceki katmandaki bir özelliğin bu hedeflere yaptığı katkıları temsil ediyor.

Lezyon aşamasında 32 sütunun 16’sı sıfıra ayarlandı. Bu sütunlara karşılık gelen yolların katkısı artık sıfır. Düzenleme sırasında da bu durum korunuyor. GPT editörleri, açık kalan bağlantıların sayısal katsayıları üzerinde çalışıyor. Dolayısıyla görevi görsel olarak şöyle okuyabiliriz: bazı yollar kapalı; kalan yolların katkısı değiştirilecek.

Bu seed’in önemli bir özelliği var. Bağlantıları kapattığımızda normal doğruluk ve olasılık kalitesi bozulmuş, fakat dengeli doğruluk yükselmiş. Daha sonra sonuçları bu nedenle tek bir “onarım yüzdesi” yerine ölçüm ölçüm yorumlayacağız. Ağın yapısına yapılan müdahale ile hangi metriğin iyi veya kötü yönde hareket ettiği ayrı gözlemler.

Bir hücrenin üzerine geldiğimizde gerçek saklanmış katsayıyı görebiliyoruz. Sonraki aşamada editörlerin bu matriste hangi hücreleri seçtiğine ve bunlara ne eklediğine bakacağız.

## 13. Here is what we asked the GPT models to do.
**Süre:** 1:42 · **Görsel adımlar:** Read the objective → Inspect the inputs and tools → Follow a proposal to its score

Şimdi GPT modellerine hangi işi verdiğimizi açıkça görelim. İki bağımsız editör de aynı görev tanımını alıyor: lezyonlu gelir sınıflandırıcısının geliştirme dengeli doğruluğunu artıracak bir yama öner. Başlangıç ağının yapısı, sınırlı ağırlık istatistikleri ve tanılama örnekleri bu göreve eşlik ediyor.

Editör birkaç tür eylem seçebiliyor. Ağırlık özetini inceleyebiliyor, belli bir matris dilimini açabiliyor, tanılama sonuçlarına bakabiliyor ve bir aday yamayı değerlendirmeye gönderebiliyor. Verdiği yanıt, koordinatörün okuyabileceği yapılandırılmış bir işlem tanımı. Koordinatör bu değişikliği hedef modele uyguluyor, modeli geliştirme kayıtlarında çalıştırıyor ve ölçümü editöre geri veriyor.

Seçim kuralı da ortak. Önce en yüksek geliştirme dengeli doğruluğu seçiliyor. Skorlar eşitse daha küçük değişiklik, ardından daha az değişen katsayı ve daha erken aday tercih ediliyor. Başlangıç modeli de karşılaştırmada bulunuyor.

Ekranda okunabilir bir özet görüyoruz. “Read the exact recorded prompt” düğmesi, repoda saklanan tam talimatı açıyor. Böylece burada kullanılan görev tanımı ile anlatım amaçlı sadeleştirmeyi birlikte inceleyebiliriz. Şimdi izin verilen iki ağırlık işlemini görelim.

## 14. Add to a few entries. Or scale a column.
**Süre:** 1:13 · **Görsel adımlar:** Add a scalar correction → Scale selected columns → Measure the complete candidate

İlk işlem, açıkça seçilmiş hücrelere sayı eklemek. Ekranda bir hücrenin eksi 0,20 olduğunu görüyoruz. Ona artı 0,03 eklediğimizde yeni katsayı eksi 0,17 oluyor. Matrisin geri kalanıyla ne yapılacağı da aynı aday yamanın içinde tanımlanıyor. Bu, tek tek belirtilen bağlantılara yapılan bir düzenleme.

İkinci işlem sütun ölçekleme. Burada bir sütundaki bütün katsayılar aynı çarpanla değişiyor. Çarpan 1,10 ise o sütunun her değeri yüzde on büyüyor; işaretleri kendi matematiksel ilişkisine göre korunuyor. Küçük dil modeli tarafında birazdan göreceğimiz aday ise seçilmiş sütunları 0,5 ile çarpıyor.

Bu iki işlem, editörün modelde kullanabildiği kontrol araçları. Editör hangi hücrelerin veya sütunların seçileceğini ve eklenecek ya da çarpılacak değerleri belirliyor. Değerlendirici, öneriyi başlangıç ağırlıklarına uygular ve ölçümü döndürür. Adaylar bu şekilde karşılaştırılıyor.

Şimdi soyut örnekten gerçek kayıtlara geçiyoruz. Birinci modelde seçilmiş Sol ve Astra yamaları aynı 16 bağlantıya dokunuyor. İlginç olan, eklenen sayıların biçiminin iki editörde farklı olması.

## 15. Sol selected sixteen different additions.
**Süre:** 1:28 · **Görsel adımlar:** Open the selected connections → Apply the saved additions → See the resulting coefficients

Sol’un seçtiği gerçek yama, ikinci katmandaki sıfır numaralı satırın 16 aktif girişini değiştiriyor. Bu satır bir hedef nörona gelen ağırlıkları içeriyor. Ekranda her hücrenin eski değeri ve eklenen düzeltme birlikte görülüyor. Müdahale uygulandıkça hücrenin yeni katsayısı hesaplanıyor.

Sol’un eklemeleri birbirinden farklı. Örneğin bazı hücrelere 0,0315, bazılarına 0,0518, bazılarına 0,0280 ekleniyor. Seçilmiş bu yamadaki 16 ekleme pozitiftir; fakat başlangıç katsayısının işaretine göre sonuç, negatif bir ağırlığı sıfıra yaklaştırmak veya pozitif bir ağırlığı büyütmek olabilir. Dolayısıyla “ağırlıkları artırmak” ifadesini bağlantının mevcut değeriyle beraber okumak gerekir.

Bu, yalnız güzel görünen bir öneri olarak kalmıyor. Yama seçildikten sonra aynı katsayılar bütün test kayıtlarında kullanılıyor. Biraz sonra bazı olasılıkların 0,5 eşiğini geçtiğini ve bunun hangi sınıflarda doğru ya da yanlış karar ürettiğini göreceğiz.

Burada anlattığımız strateji, kaydedilmiş aday işlemleri ve seçilmiş yamanın gözlenen yapısıdır. Sol’un iç düşünce sürecini tahmin etmek yerine, gerçekten ürettiği ve değerlendirmeye gönderdiği sayıları izliyoruz.

## 16. Astra selected +0.003 on each of sixteen entries.
**Süre:** 1:28 · **Görsel adımlar:** Read the candidate trajectory → Compare the final tie → Select the smaller addition

Astra’nın kaydedilmiş denemelerinde daha belirgin bir büyüklük araması görüyoruz. Aynı 16 bağlantıya çeşitli eşit eklemeler deniyor. Pozitif 0,03, negatif 0,03 ve daha küçük pozitif değerler bunların arasında. Her nokta, o adayın geliştirme panelindeki dengeli doğruluğunu gösteriyor.

Grafikte ilk bakışta küçük görünen farklar, aday seçiminde kullanılıyor. Son iki önemli adayda her bağlantıya 0,005 ve 0,003 eklenmiş. Bu iki aday aynı en iyi geliştirme dengeli doğruluğuna ulaşıyor. Seçim kuralı eşit skor durumunda daha küçük müdahaleyi tercih ettiği için 0,003 seçiliyor.

Böylece Astra’nın son yaması son derece somut: aynı 16 hücrenin her birine artı 0,003. Sol’da hücreye göre değişen eklemeler vardı; burada bütün seçili hücrelere eşit bir adım var. Bu farklılık daha sonra test sonuçlarına da yansıyor: Astra’nın seçilmiş yaması, test dengeli doğruluğunu başlangıç seviyesinin çok yakınında bırakıyor.

Geliştirmede küçük bir kazanım görmekle son testte aynı kazanımı elde etmek arasındaki ilişkinin ölçülmesi, bu deneyin önemli parçalarından biri. Ortak çalışma aşaması da bu kaydedilmiş denemeleri bilgi olarak kullanıyor.

## 17. Proposal → review → measurement → next round.
**Süre:** 2:26 · **Görsel adımlar:** Bring in prior development history → Propose and review a patch → Return measured feedback → Inspect the selected joint patch

Şimdi iki editörün birlikte çalıştığı aşamaya geliyoruz. Ortak oturumun önünde hem Sol’un hem Astra’nın önceki geliştirme denemeleri var. Bu geçmiş, hangi yamanın denendiğini ve hangi ölçümün döndüğünü içeriyor. Ortak oturum kendi değişikliklerini yine aynı başlangıç modeline göre tanımlıyor.

Bir turda editörlerden biri tam bir yama öneriyor. Diğeri bu öneriyi inceliyor; aynı yamayı kabul edebiliyor, yerine tam bir revize yama verebiliyor veya başlangıç durumunu tercih edebiliyor. Değerlendirici yalnız bu inceleme sonrasındaki seçeneği ölçüyor. Elde edilen geri bildirim iki editöre de dönüyor. Bir sonraki turda öneren ve inceleyen rolleri yer değiştiriyor.

Beş tur dediğimiz şey, bu öneri, inceleme ve tek ölçüm döngüsünün beş kez yürütülmesi. Ekrandaki yuvalar bu tamamlanan denemeleri temsil ediyor. Dolayısıyla iki ismin yan yana durmasından daha somut bir işbirliği biçimini ölçüyoruz: sırayla öneri üretme, diğerinin önerisini değerlendirme ve ortak ölçüm geçmişi kullanma.

Seçilen Adult ortak yaması ilginç derecede basit bir ilişki taşıyor. Sol’un seçilmiş eklemelerinin her biri 0,93 ile çarpılmış. Bu, kaydedilmiş yamalardan doğrudan hesaplanan bir özellik. Ortak çalışma Sol’un vektörünün büyüklüğünü biraz azaltmış. Bunun performans sonucunu ayrıca ölçtük; matematiksel benzerliğin başarıya nasıl yansıdığını birazdan göreceğiz.

## 18. One stored coefficient, three edits.
**Süre:** 1:13 · **Görsel adımlar:** Starting coefficient → Astra’s chosen value → Sol’s chosen value → Joint’s chosen value

Bütün matrisi bir an için geride bırakıp aynı bağlantıya odaklanalım. Bu bağlantı, önceki katmanın 15 numaralı özelliğini ikinci katmanın sıfır numaralı nöronuna bağlıyor. Başlangıç katsayısı yaklaşık 0,12482.

Astra bu hücreye 0,003 ekliyor ve değer yaklaşık 0,12782 oluyor. Sol’un eklemesi 0,028; onun son katsayısı yaklaşık 0,15282. Ortak yama ise bu hücrede Sol’un eklemesinin yüzde 93’ünü, yani 0,02604’ü kullanıyor; değer yaklaşık 0,15086 oluyor.

Sağdaki sayı, bu katsayının gelen aktivasyonla çarpılmasından oluşan katkı. Gösterim için aktivasyonu 2 seçtiğimizde başlangıç katkısı yaklaşık 0,24964, Sol’daki katkı yaklaşık 0,30564. Aradaki fark, tek bağlantının hedef nöronun toplamına yaptığı değişiklik.

Bu aktivasyon değeri bir hesap örneği; saklanmış gerçek katsayılarla aynı çarpma işlemini görünür kılıyor. Sürgüyü oynattığımızda bütün katkılar aynı anda yeniden hesaplanıyor. Şimdi bu tür küçük katkı değişikliklerinin gerçek test kayıtlarındaki final olasılıklarına nasıl yansıdığına geçiyoruz.

## 19. A small probability shift can cross the decision threshold.
**Süre:** 1:28 · **Görsel adımlar:** Read the starting probabilities → Apply the selected Sol patch → Compare with the true classes

İki kaydın gerçek saklanmış tahminlerini yan yana görüyoruz. İlk kaydın başlangıç olasılığı yaklaşık 0,49274. Sol yaması uygulandığında 0,50948 oluyor. Karar eşiği 0,5 olduğu için model artık üst gelir sınıfını seçiyor. Bu kaydın gerçek etiketi de üst gelir sınıfı; dolayısıyla karar düzelmiş oluyor.

İkinci kaydın başlangıç olasılığı yaklaşık 0,49516. Düzenlemeden sonra 0,50781’e çıkıyor. Tahmin yine aynı yönde değişiyor ve üst gelir sınıfına geçiyor. Fakat bu kaydın gerçek etiketi alt gelir sınıfı. Bu kez aynı yöndeki olasılık hareketi, doğru bir kararı yanlış karara dönüştürüyor.

Bu iki örnek, modelin davranışının neden tek bir “daha iyi” kelimesiyle açıklanamadığını somutlaştırıyor. Bir ağırlık yaması birçok kaydı aynı anda etkiliyor. Bazı kayıtları doğru tarafa, bazılarını yanlış tarafa taşıyabiliyor. Sonucun iyi olup olmadığı, hangi görevi ve hangi ölçüm kuralını önemsediğimize bağlı.

Şimdi bu iki örneği bütün test kümesine genişletelim. Sonraki sahnede kaç kararın hangi sınıfta değiştiğini göreceğiz; ardından bunların iki doğruluk metriğine nasıl dönüştüğünü hesaplayacağız.

## 20. 65 recovered decisions. 102 newly incorrect decisions.
**Süre:** 1:13 · **Görsel adımlar:** Count the recovered decisions → Count the newly incorrect decisions → Keep the class sizes visible

Sol’un seçilmiş yaması için bütün test kayıtlarını başlangıç modeliyle eşleştirdik. Gerçekte üst gelir sınıfında bulunan 65 kayıt, yanlış tahminden doğru tahmine geçmiş. Gerçekte alt gelir sınıfında bulunan 102 kayıt ise doğru tahminden yanlış tahmine geçmiş.

Sahnede işaretlerin hareketini bu iki sınıf için ayrı izliyoruz. Bu ayrım önemli, çünkü sınıfların büyüklükleri eşit değil. Test kümesinde 3.846 üst gelir, 12.435 alt gelir kaydı var. Bir sınıfta 65 örneklik değişimle diğer sınıfta 102 örneklik değişim, sınıf içindeki oranlar bakımından farklı anlamlar taşıyor.

Ortak yamanın sayıları da aynı yapıda: 59 üst gelir kaydı düzeliyor, 96 alt gelir kaydı yanlış tarafa geçiyor. Şu anda temel mekanizmayı Sol üzerinden izliyoruz; ortak sonucun neden ona yakın olduğunu bu sayılarla da anlayabiliriz.

Bu aşamaya kadar bir ağırlık düzenlemesinden başlayıp tek kaydın olasılığına, oradan kararına ve bütün değişen kararların sayımına geldik. Bir sonraki adım, bu sayıların nasıl tek bir başarı ölçüsüne dönüştürüldüğü.

## 21. The two accuracy metrics weight records differently.
**Süre:** 1:57 · **Görsel adımlar:** Calculate ordinary accuracy change → Calculate the change per class → Average the two class changes

Normal doğrulukta her kayıt aynı ağırlıkla sayılır. Sol yaması 65 doğru karar kazandırırken 102 doğru kararı kaybettiriyor. Net değişim eksi 37 doğru karar. Bunu 16.281 test kaydına böldüğümüzde normal doğrulukta yaklaşık eksi 0,2273 yüzde puanlık değişim elde ediyoruz.

Dengeli doğruluk ise her sınıfın kendi doğru bulunma oranını hesaplayıp bu iki oranın ortalamasını alır. Üst gelir sınıfındaki değişim 65 bölü 3.846. Alt gelir sınıfındaki değişim eksi 102 bölü 12.435. Bu iki sınıf oranını eşit ağırlıkla ortaladığımızda artı 0,4349 yüzde puan elde ediyoruz.

Dolayısıyla aynı model yaması için iki farklı yön görüyoruz: normal doğruluk biraz azalırken dengeli doğruluk artıyor. Burada bir hesap çelişkisi yok. İki ölçüm farklı önceliklerle toplama yapıyor. Dengeli doğruluk, azınlık sınıfının oranına çoğunluk sınıfıyla aynı ağırlığı veriyor.

Bu çalışmada aday seçimi için baştan dengeli doğruluk kullanılmıştı. Sonuçları değerlendirirken normal doğruluk ve olasılık kalitesi de birlikte raporlandı. Şimdi dört seçilmiş modelin toplu tablosuna baktığımızda, hangi sayının hangi karar değişiminden çıktığını biliyoruz.

## 22. The class-balanced score increased.
**Süre:** 1:28 · **Görsel adımlar:** Compare balanced accuracy → Read the paired intervals → Compare the other metrics

Birinci araştırma sorusunun cevabı burada. Başlangıçtaki lezyonlu modelin test dengeli doğruluğu yüzde 78,5858. Sol’un seçtiği yama bunu yüzde 79,0207’ye, ortak yama yüzde 78,9668’e taşıyor. Astra’nın sonucu yüzde 78,5855 ile başlangıca çok yakın.

Farklar açısından Sol artı 0,4349, ortak yama artı 0,3810 yüzde puan getiriyor. Grafikteki aralıklar, aynı test kayıtları üzerinde yapılan eşleştirilmiş yeniden örneklemeyle hesaplanmış. Bu aralıklar, bu seçilmiş modellerin örnek belirsizliğini anlatıyor. Farklı seed’lerde veya yeni editör oturumlarında oluşabilecek değişkenlik ayrı bir araştırma konusu.

Diğer ölçümler de hikâyenin parçası. Sol ve ortak yamada normal doğruluk yaklaşık yüzde 82,86’dan yüzde 82,63’e düşüyor. Log-loss ve Brier artıyor; yani olasılık kalitesi de aynı anda iyileşmiş değil. Temiz ağ referansının normal doğruluğu ve olasılık kalitesi daha iyi, dengeli doğruluğu ise lezyonlu başlangıçtan düşük.

Bu seed’de ulaştığımız sonuç, kalan bağlantılara yapılan küçük sayısal müdahalenin karar dengesini değiştirebildiği. Hangi yöndeki değişimi değerli bulduğumuz, seçtiğimiz görev ölçütüne ve hata maliyetlerine bağlı.

## 23. The joint selection finished close to Sol.
**Süre:** 1:13 · **Görsel adımlar:** Compare the two selections → Read their direct difference → Interpret the measured scope

Üçüncü araştırma sorusuna dönersek, ortak çalışma seçilmiş son modelde Sol’a çok yakın bir sonuç veriyor. Sol’un dengeli doğruluğu yüzde 79,0207; ortak modelinki yüzde 78,9668. Doğrudan fark yaklaşık eksi 0,0539 yüzde puan.

Bu farkın eşleştirilmiş yüzde 95 aralığı yaklaşık eksi 0,1260 ile artı 0,0062 arasında. Aralık sıfırın iki tarafına uzanıyor. Bu ölçüm, ortak çalışmanın Sol’u aştığını gösteren bir sonuç sağlamıyor; gözlenen son modeller birbirine yakın.

Karşılaştırmanın çalışma biçimini de doğru tarif edelim. Adult bağımsız aramaları on adaylık izinle yürütülmüş; ortak çalışma önceki geliştirme kayıtlarını kullanarak beş yeni tur yapmış. Dolayısıyla bu sonuç, seçilen uç noktaların karşılaştırması. İşbirliğinin kendisinin, daha fazla toplam bilgi ve hesap harcamasından bağımsız katkısını ölçmek için eşit bütçe ve geçmiş erişimiyle yeni koşullar tasarlanabilir.

Biz burada ortak yamanın somut biçimini ve onun ölçülmüş sonucunu gördük. Yama Sol’un eklemelerini yüzde yedi küçültmüş; karar değişimleri ve final skor da ona yakın çıkmış. Şimdi ikinci hedefte, küçük dil modelinde aynı arama fikrinin nasıl sonuç verdiğini görelim.

## 24. The second target answers multiple-choice questions.
**Süre:** 1:28 · **Görsel adımlar:** Meet the 1.7B-parameter model → Open the two task families → Follow answer selection

İkinci hedef, önceden eğitilmiş SmolLM2-1.7B. Buradaki 1,7 milyar ifadesi modelin yaklaşık parametre sayısı. Bu modeli bizim Census ağımız gibi sıfırdan eğitmedik; yayımlanmış ağırlıkları başlangıç olarak kullandık ve belirli MLP çıkış matrislerinde düzenleme aradık.

Görevlerden biri ARC-Easy: okul düzeyinde bilim sorularında doğru seçeneği bulmak. Diğeri PIQA: fiziksel dünyayla ilgili bir amaca ulaşmanın daha uygun yolunu seçmek. İki görev de burada seçenek metinlerinin model tarafından puanlanması üzerinden değerlendiriliyor.

Ekrandaki iletkenlik sorusu bir anlatım örneği. Model, soru bağlamından sonra her aday cevabın ne kadar olası olduğunu hesaplıyor. Benchmark kuralı bu sayıları bir seçim kuralına dönüştürüyor. Birazdan bu hesabı da açacağız; böylece accuracy değerinin nereden geldiğini takip edeceğiz.

Bu hedefte kaynak Qwen deneyindeki gibi önceden saptanmış güçlü bir tekrar arızasını onarmıyoruz. Araştırma sorumuz, sınırlı ağırlık değişikliklerinin bu hazır modelin çoktan seçmeli cevap seçimini artırıp artırmadığı. Editörlere verilen talimat ve geri bildirim de buna göre kurulmuş.

## 25. A clear objective and a bounded part of the model.
**Süre:** 1:28 · **Görsel adımlar:** Read the task → Locate the editable weights → Read the feedback and selection rule

SmolLM2 editörlerinin hedefi, geliştirme ARC-Easy normalized accuracy değerini artırmak. Başlangıç görünümünde modelin mimarisi, sınırlı tensor istatistikleri, 128 eğitim tanılama sorusunun etiketleri ve tahminleri ile 128 örneklik geliştirme panelinin başlangıç skoru bulunuyor.

Düzenlenebilen alan transformer katmanlarının MLP çıkış matrisleri. Editör, seçtiği sütunları ölçekleyebiliyor veya belirli hücrelere açık sayısal eklemeler verebiliyor. Ağırlık değişikliğinin büyüklüğünü ve kapsadığı katsayı sayısını sınırlayan kurallar uygulanıyor. Böylece adayların hepsi aynı türden ölçülebilir müdahaleler olarak değerlendirmeye giriyor.

Araç eylemleri yine inceleme, aday ölçümü ve son seçim etrafında dönüyor. Editör örnekleri veya katsayıları incelemek için izinli çağrıları yapıyor; bir değişiklik öneriyor; değerlendirici modeli çalıştırıp geliştirme skorunu döndürüyor. En yüksek normalized accuracy seçiliyor. Eşitlikte daha küçük ağırlık değişikliği tercih ediliyor.

Tam prompt ekranın düğmesinden açılabiliyor. Bu sayfa, “Sol ve Astra burada neye göre karar veriyor?” sorusunun cevabını taşıyor: görev hedefi, görülebilen tanılama bilgisi, uygulanabilen işlem ailesi ve geri dönen ölçüm birlikte karar sürecini oluşturuyor.

## 26. One proposal halved 32 output columns.
**Süre:** 1:42 · **Görsel adımlar:** Enter the MLP output matrix → Select the first 32 columns → Apply ×0.5 → Read the development result

Şimdi kaydedilmiş gerçek bir SmolLM2 adayını görüyoruz. Müdahale, 23 numaralı transformer katmanının MLP çıkış matrisi üzerinde. Bu matris, MLP içindeki özelliklerin katkılarını bir araya getirip katman çıktısına taşıyor.

Aday işlem ilk 32 sütunu, yani sıfırdan 31’e kadar olan sütunları seçiyor. Bu sütunlardaki katsayılar 0,5 ile çarpılıyor. Böylece bu iç özelliklerin çıkışa yazdığı katkı azaltılıyor. Gerçek uygulamada 65.536 katsayı değişmiş; bu sayıyı saklanmış aday kaydından biliyoruz.

Burada büyük bir dil modelinin tamamını ekranda tek tek göstermeye çalışmıyoruz. Kamerayı değişikliğin yapıldığı parçaya getirip seçilmiş işlemi izliyoruz. Matris çizimi işlem alanının şeması; ekranda uydurulmuş ham LM katsayıları kullanmak yerine saklanan sütun indeksleri, ölçekleme çarpanı ve değişiklik sayısı gösteriliyor.

Bu aday geliştirme normalized accuracy değerini yüzde 75’te bırakmış; başlangıç da aynı skorda. Dolayısıyla sayılar değişmiş olsa bile seçim ölçüsünde ilerleme oluşmamış. Bu ayrım dil modeli sonucunu anlamak için belirleyici: bir müdahalenin uygulanmasıyla, o müdahalenin seçilmesi iki ayrı aşama.

## 27. Each answer receives a likelihood score.
**Süre:** 1:28 · **Görsel adımlar:** Score candidate continuations → Normalize by answer-text length → Select and check an answer

Bir adayın puanı, seçenekler üzerinden hesaplanıyor. Model her cevap metni için, sorudan sonra bu devamın oluşma log-olasılığını veriyor. Bunlar genellikle negatif sayılar; daha büyük, yani sıfıra daha yakın değer daha yüksek olasılığı temsil ediyor.

Bu çalışmanın acc_norm kuralı, her devamın toplam log-olasılığını cevap metninin karakter sayısına bölüyor. Token sayısı yerine karakter sayısı kullanılması, sabitlenmiş benchmark scorer’ının tanımı. Ekrandaki basit örnekte bakır için eksi 1,2 toplam değeri altı karaktere bölünüp eksi 0,2 oluyor. Diğer seçenekler de aynı kuralla hesaplanıyor.

En yüksek normalize değeri alan cevap seçiliyor ve doğru cevap anahtarıyla karşılaştırılıyor. Bu doğruluk göstergeleri bütün geliştirme sorularında toplanarak adayın normalized accuracy puanını oluşturuyor. Ekrandaki soru ve log-olasılıklar, bu kuralı açıklamak için kurulmuş hesap örneği; final skorlar ayrı saklanmış model tahminlerinden geliyor.

Bu süreçte bir ağırlık değişikliği bazı olasılıkları değiştirebilir, ama en üst sıradaki cevap aynı kalabilir. Bu yüzden beş adayın farklı katsayılara sahip olması, doğruluk eğrisinin mutlaka farklı noktalara gitmesi anlamına gelmiyor. Şimdi gerçek geliştirme eğrilerine bakalım.

## 28. The search selected the original weights.
**Süre:** 1:42 · **Görsel adımlar:** Compare the development trajectories → Resolve ties with change size → Evaluate the selected state

Sol ve Astra’nın her biri beş aday denemesini ölçmüş. Ortak aşama da beş deneme yapmış; ilk ortak deneme geçersiz olduğu için o denemeye bir skor yazılmamış. Ekranda yalnız ölçülmüş adaylar görünüyor.

Başlangıç normalized accuracy değeri yüzde 75. İki bağımsız aramada ikinci aday yüzde 74,21875’e düşüyor. Diğer kaydedilmiş geçerli adaylar başlangıçla aynı yüzde 75 seviyesinde kalıyor. En yüksek skor eşit olduğunda daha küçük ağırlık değişikliği seçildiği için, bütün koşullar başlangıç modeline dönüyor. Başlangıcın değişiklik büyüklüğü sıfır.

Bunun önemli sonucu şu: finalde dört isim var ama tek bir gerçek ağırlık durumu seçilmiş. Bu nedenle aynı modelin tahminlerini dört bağımsız gözlem gibi yorumlamıyoruz. Seçilen durumda ARC-Easy normalized accuracy 376 bölü 512, yani yüzde 73,44. PIQA için 201 bölü 256, yani yüzde 78,52.

İkinci araştırma sorusunun bu koşuldaki cevabı, bu müdahale ailesi ve arama bütçesinin başlangıçtan daha iyi bir seçilmiş model üretmemesi. Bu, elde edilen gerçek bir araştırma sonucu ve sonraki deneyi hangi yönde geliştireceğimize dair bir başlangıç noktası.

## 29. Three questions. Three measured answers.
**Süre:** 1:28 · **Görsel adımlar:** Answer the classifier question → Answer the language-model question → Answer the collaboration question

Şimdi başta koyduğumuz üç soruya tek ekranda dönelim. Birinci soruda doğrudan ağırlık düzenlemeleri, küçük gelir ağının sınıfları eşit ağırlıklandıran doğruluğunu değiştirebildi. Sol ve ortak yama bu ölçümde yükseldi. Bunun arkasında hangi kayıtların doğru veya yanlış tarafa geçtiğini de gördük. Aynı zamanda normal doğruluk ve olasılık kalitesindeki bedeli ölçtük.

İkinci soruda, küçük dil modeli üzerindeki sınırlı arama başlangıç modelini seçti. Denenen adaylar sayısal müdahaleler içeriyordu; seçim ölçüsünde başlangıcın üzerine çıkan bir son aday oluşmadı. ARC-Easy ve PIQA skorları seçilmiş bu ortak başlangıç durumunun ölçümü.

Üçüncü soruda, önceki denemelerin bilgisiyle çalışan ortak oturum Sol’a yakın bir son yama ve yakın bir final skor üretti. Ortak modelin en iyi bağımsız seçimin üstüne çıktığını gösteren bir üstünlük elde etmedik.

Bu küçük çalışma seed 101 ve kaydedilmiş oturumlarla sınırlı bir keşif karşılaştırması. Yayınlanan LM v2 ölçümleri, önceki sürümde görülmüş panelleri yeniden kullanıyor. Bu kapsam içinde çalışmanın değeri, öneriden katsayıya, katsayıdan karara ve karardan ölçüme uzanan zinciri somut olarak gösterebilmemiz. Son olarak bu bulgulardan hangi yeni deneylere gidilebileceğine bakalım.

## 30. Make the next intervention more informative.
**Süre:** 1:22 · **Görsel adımlar:** Target mechanisms → Optimize the decision tradeoff → Measure the value of collaboration

Birinci yön, müdahaleleri daha fazla mekanizma bilgisiyle beslemek. Kaynak çalışmada güçlü örnek, belirli bir tekrar davranışının iç katkısını teşhis edip onu hedeflemekti. Bizim sonraki dil modeli deneyimizde de aktivasyon kanıtıyla seçilmiş yönler ve daha zengin ama açıkça tanımlanmış düzenleme alanları araştırılabilir. Burada amaç, editörün yalnız bir skoru yükseltmesini istemek yerine belirli bir davranış hipotezini test etmek.

İkinci yön karar hedefi. Gelir modelinde dengeli doğruluk artarken başka ölçümlerin gerilediğini gördük. Sonraki çalışma, hata maliyetlerini ve olasılık kalitesini daha açık bir çok ölçütlü hedefe bağlayabilir. Hangi yanlış kararın daha önemli olduğu tanımlandığında, aramanın iyi sonuç tanımı da daha anlamlı olur.

Üçüncü yön işbirliği. Aynı toplam bütçe, aynı geçmiş bilgisine erişim ve birden fazla bağımsız oturumla ortak çalışmanın hangi parçasının katkı verdiğini ayırabiliriz. Öneri çeşitliliği mi, inceleme mi, geçmiş denemelerden öğrenme mi? Bunlar ölçülebilir yeni sorular.

Bugünkü ana sonuç, dil modellerinin önerilerini gerçek ağırlık değişikliklerine dönüştürüp bunların karar etkisini izleyebildiğimiz bir deney oluşturmuş olmamız. Şimdi tartışmayı şu soruyla açabiliriz: hangi model davranışlarında böyle doğrudan, gerekçeli müdahaleler en fazla değer yaratabilir?

## Kaynaklar

- Deney yayını: https://github.com/detasar/llm-weight-editing-study/tree/d78bd5edbb84adb429f95f4c06ca4b70d1277d86
- Kaynak araştırma: https://rikiyat.github.io/blog/weight-space-programming/
- Kaynak araba deneyi: https://github.com/RikiyaT/lm_understand-logs/tree/main/exp4_fix_car
- Kaynak matematik deneyi: https://github.com/RikiyaT/lm_understand-logs/tree/main/exp8_math

Türkçe metin, kaynaklardan yapılan açıklamalı bir anlatımdır. İşlemlerin gizli iç muhakemesini temsil etmez. Hesap örnekleri sunumda ayrıca işaretlenmiştir.