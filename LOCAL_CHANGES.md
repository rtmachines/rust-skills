# Poprawiona wersja Rust Skills

Wersja **1.5.1+local.1**, przygotowana 23 października 2026 r. na podstawie
[commita fd2a861ab0406a4ac536a55274d14ea6fd1ca9c9](https://github.com/leonardomso/rust-skills/tree/fd2a861ab0406a4ac536a55274d14ea6fd1ca9c9).

Poprawiono wszystkie **101 potwierdzonych ustaleń F01–F101** z recenzji, w tym
3 o wadze wysokiej. Zachowano 265 reguł w 26 kategoriach, ich angielski język,
identyfikatory i licencję MIT. Zmiany dotyczą 109 plików reguł oraz indeksu,
opisu wersji i narzędzi weryfikacji. Plik porównawczy
`type-newtype-validated.md` był już poprawny i pozostał bez zmian.

Oryginalny checkout pozostał niezmieniony. Poprawki przygotowano w osobnym
lokalnym repozytorium na gałęzi `local-corrections`. Na życzenie właściciela
24 października 2026 r. przygotowano je do publikacji na gałęzi `master` w
[forku rtmachines/rust-skills](https://github.com/rtmachines/rust-skills).
Nie zainstalowano skilla w konfiguracji żadnego agenta.

Publikowana wersja obejmuje reguły, testy i przenośny rejestr ustaleń.
Surowe logi weryfikacji pozostają lokalnie i są pomijane przez `.gitignore`.
Odwołania `local-verification/...` w rejestrze identyfikują te lokalne dowody;
nie są linkami do plików dostępnych w forku. Wyniki nadal opisują przebiegi
wykonane 23 października, wraz z ich pierwotnymi ograniczeniami.

## Najważniejsze zmiany

- Naprawiono bezpieczne API oparte na surowych wskaźnikach i kontrole granic
  wymagane również w release; rozmiar macierzy nie może przepełnić się przed
  dostępem przez `get_unchecked`.
- SIMD łączy elementy według wspólnych indeksów. Transakcje zachowują blokadę
  do końca, a scratch arena resetuje się po wywołaniu i przy unwinding.
- Przykłady asynchroniczne kończą pracę po zamknięciu kanałów i obserwują
  zakończenie zadań. Zalecenia o mutexach rozróżniają blokady blokujące i async.
- Poprawiono przykłady API, makr, konwersji, obsługi UTF-8, błędów, Serde,
  testów, manifestów, widoczności modułów i dokumentacji.
- Usunięto nieuzasadnione obietnice wydajności i pełnego wykrywania UB.
  Doprecyzowano wymagania wersji, edition, konfiguracji i własności zasobów.
- Wygenerowano ponownie indeks z aktualnych streszczeń. Zalecony profil Cargo
  przedstawia teraz opcjonalne ustawienia wymagające świadomego wyboru.

## Wykonana weryfikacja

Podstawowy kompilator: **rustc 1.99.0 (b940084d7 2026-09-28)**, edition 2024,
`x86_64-pc-windows-msvc`. SIMD: **nightly-2026-05-22**,
`rustc 1.97.0-nightly (e96c36b6f 2026-05-21)`. Manifest MSRV sprawdzono dodatkowo
na **Rust 1.85.0**. Zależności i szczegółowe ograniczenia opisują poszczególne
zestawy; podstawowe manifesty regresji zawierają przypięte wersje i lockfile.

| Zestaw | Wykonany wynik |
|---|---|
| Pamięć, liczby, granice API | 38 testów debug + te same 38 testów release; wszystkie przeszły |
| Portable SIMD | 1 test obejmujący 2560 kombinacji przesunięć i długości, ze zróżnicowanymi wartościami; przeszedł |
| API i typy | 27 prób kompilacyjnych: 16 akceptacji i 11 oczekiwanych odrzuceń; dodatkowo 22 testy wykonania; wyniki zgodne |
| Async, runtime i biblioteki | 32 testy, 26 modułów wyodrębnionych z Markdown; wszystkie przeszły |
| Dokumentacja i narzędzia | 13 grup, 48 poleceń; wszystkie przeszły; celowane uzupełnienie jednej grupy: 11 poleceń |
| Doctesty w grupie dokumentacji | 5 przeszło, w tym jeden `no_run` sprawdzony kompilacyjnie |
| Struktura i indeks | 265 reguł poprawnych strukturalnie; indeks aktualny |
| Diff | `git diff --check` bez błędów |

Nie sumujemy powtórzeń debug/release ani celowanego ponownego sprawdzenia jako
nowych, niezależnych przypadków. Testy czytają aktualne przykłady Markdown;
niektóre dodają brakujące typy domenowe lub model zasobu. Sprawdzono także
oczekiwane odmowy kompilacji, ich diagnostykę oraz kolejność sprzątania podczas
paniki. Nie uruchamiano wywołań o znanym niezdefiniowanym zachowaniu.

Instrukcje odtwarzania: [checks/regressions/README.md](checks/regressions/README.md).
Maszynowy rejestr rozwiązań i weryfikacji: [CORRECTIONS.json](CORRECTIONS.json).

## Ograniczenia

Pełny starszy mechanizm wyodrębniania przykładów **nie uzyskał wyniku
kompilacji**. Generator przygotował 830 plików z 1136 bloków Rust, ale próba
Cargo offline na 1.99.0 zatrzymała się przed kompilacją: w cache brakowało
przypiętego `anyhow 1.0.102`. Oryginalny toolchain CI 1.95.0 nie był
zainstalowany. Nie zmieniono baseline, aby uznać nowe błędy za dopuszczalne.

Nie wykonano pełnej macierzy 1.95/1.96, Linux, 32-bit ani Miri. Nie przeprowadzono
nowych benchmarków uzasadniających ogólne przyspieszenia. Mockall wykonano na
dostępnej wersji 0.15.0; opis polityki Insta zweryfikowano w źródle pierwotnym,
bez uruchamiania Insta. Testy FFI z rzeczywistym `memcpy` obejmują prawidłowe
wycinki; pozostałe hipotetyczne symbole FFI sprawdzono tylko kompilacyjnie.
Modele usług i transakcji nie zastępują integracji z rzeczywistymi systemami.

Poprawienie ustaleń recenzji nie jest gwarancją braku wszystkich możliwych błędów
w kolekcji. Zachowano przykłady celowo niepoprawne w sekcjach „Bad” oraz fragmenty
wymagające kontekstu. Szczegóły warunków należy czytać w pełnych regułach.

## Rejestr ustaleń

Każdy wiersz oznacza wdrożoną poprawkę. Obejmuje też lokalizacje porównawcze,
które sprawdzono bez potrzeby zmiany. Szczegółowa metoda, rozwiązanie i
ograniczenia są powiązane z tym samym identyfikatorem w `CORRECTIONS.json`.

| ID | Ustalenie z recenzji | Poprawione lub sprawdzone pliki |
|---|---|---|
| F01 | Bezpieczne funkcje dopuszczają niezdefiniowane zachowanie przez surowe wskaźniki | [lint-unsafe-doc.md](rules/lint-unsafe-doc.md), [unsafe-extern-block.md](rules/unsafe-extern-block.md), [unsafe-minimize-scope.md](rules/unsafe-minimize-scope.md) |
| F02 | Przepełnienie rozmiaru macierzy unieważnia uzasadnienie dla get_unchecked | [opt-bounds-check.md](rules/opt-bounds-check.md) |
| F03 | Iloczyn skalarny SIMD łączy elementy o różnych indeksach i pomija dane | [opt-simd-portable.md](rules/opt-simd-portable.md) |
| F04 | Przykład kontroli kolejności destruktorów zwalnia blokadę przed zatwierdzeniem transakcji | [mem-drop-order.md](rules/mem-drop-order.md) |
| F05 | Reset współdzielonej areny powoduje panic z powodu aktywnego pożyczenia | [mem-arena-allocator.md](rules/mem-arena-allocator.md) |
| F06 | Obietnica zwolnienia całej pamięci żądania przez Bump pomija destruktory | [mem-arena-allocator.md](rules/mem-arena-allocator.md) |
| F07 | Pętle async nie obsługują stanów końcowych kanału lub wejścia | [async-cancel-safety.md](rules/async-cancel-safety.md), [async-mpsc-queue.md](rules/async-mpsc-queue.md), [async-select-racing.md](rules/async-select-racing.md), [async-watch-latest.md](rules/async-watch-latest.md) |
| F08 | Wyjście z funkcji nie anuluje automatycznie tokenów potomnych | [async-cancellation-token.md](rules/async-cancellation-token.md) |
| F09 | Tabela cancellation safety myli zachowanie zasobu z zachowaniem postępu operacji | [async-cancel-safety.md](rules/async-cancel-safety.md) |
| F10 | Bezwzględny zakaz blokady przez await jest sprzeczny z API Tokio i dalszą treścią | [SKILL.md](SKILL.md), [anti-lock-across-await.md](rules/anti-lock-across-await.md), [async-bounded-channel.md](rules/async-bounded-channel.md), [async-clone-before-await.md](rules/async-clone-before-await.md), [async-no-lock-await.md](rules/async-no-lock-await.md) |
| F11 | trait-variant nie tworzy opisanego wariantu dyn przez boxing | [async-fn-in-trait.md](rules/async-fn-in-trait.md) |
| F12 | AsyncFn + Send nie oznacza, że future zwrócone przez wywołanie jest Send | [async-async-fn-bounds.md](rules/async-async-fn-bounds.md) |
| F13 | timeout otrzymuje wynik try_join!, a nie future | [async-try-join.md](rules/async-try-join.md) |
| F14 | Deklarowany MSRV 1.80 jest niezgodny z edition 2024 | [proj-msrv-declare.md](rules/proj-msrv-declare.md) |
| F15 | Cargo nie pozwala ustawiać lto w profilu pojedynczego pakietu | [perf-release-profile.md](rules/perf-release-profile.md) |
| F16 | Poprawne przykłady FFI nadal zawierają extern niedopuszczalne w edition 2024 | [type-repr-transparent.md](rules/type-repr-transparent.md), [unsafe-extern-block.md](rules/unsafe-extern-block.md) |
| F17 | Nazwa lifetime 'de uniemożliwia pokazany derive Deserialize | [name-lifetime-short.md](rules/name-lifetime-short.md) |
| F18 | Przykład przygotowany dla Loom nie kompiluje się po wybraniu typów Loom | [test-loom-concurrency.md](rules/test-loom-concurrency.md) |
| F19 | Miri i Loom otrzymują zbyt szerokie gwarancje wykrywania błędów | [conc-atomic-ordering.md](rules/conc-atomic-ordering.md), [test-loom-concurrency.md](rules/test-loom-concurrency.md), [unsafe-miri-ci.md](rules/unsafe-miri-ci.md) |
| F20 | clamp z NaN w granicy powoduje panic, a nie nieokreślony wynik | [num-saturating-clamp.md](rules/num-saturating-clamp.md) |
| F21 | pub(super) w module parser udostępnia elementy także modułowi codegen | [proj-pub-crate-internal.md](rules/proj-pub-crate-internal.md), [proj-pub-super-parent.md](rules/proj-pub-super-parent.md) |
| F22 | Newtype zawierający String nie może implementować Copy | [api-newtype-safety.md](rules/api-newtype-safety.md), [type-newtype-validated.md](rules/type-newtype-validated.md) |
| F23 | Zastąpienie zwracanego Self przez Box<Self> nie przywraca dyn compatibility | [trait-object-safety.md](rules/trait-object-safety.md) |
| F24 | Przykład oszczędzania paddingu zakłada kolejność pól niegwarantowaną przez repr(Rust) | [mem-smaller-integers.md](rules/mem-smaller-integers.md) |
| F25 | Opis floatów myli równość liczbową z bitową i pozycję wszystkich NaN | [num-float-compare.md](rules/num-float-compare.md) |
| F26 | Przykład Serde z literówką już odrzuca wejście bez deny_unknown_fields | [serde-default-compat.md](rules/serde-default-compat.md), [serde-deny-unknown-fields.md](rules/serde-deny-unknown-fields.md) |
| F27 | unsafe_op_in_unsafe_fn jest domyślnie ostrzeżeniem, nie twardym błędem edition 2024 | [unsafe-minimize-scope.md](rules/unsafe-minimize-scope.md) |
| F28 | Cell nie jest analogiczne do Rc pod względem Send | [unsafe-send-sync-manual.md](rules/unsafe-send-sync-manual.md) |
| F29 | Optymalizacja Result z NonZero wymaga warunków dotyczących drugiego wariantu | [num-nonzero.md](rules/num-nonzero.md) |
| F30 | Opis wartości lto = false i lto = "off" jest odwrócony | [opt-lto-release.md](rules/opt-lto-release.md) |
| F31 | Reset bumpalo nie ma bezwarunkowo stałego kosztu | [mem-arena-allocator.md](rules/mem-arena-allocator.md) |
| F32 | Bezpieczny get_unchecked traci jedyne sprawdzenie granic w release | [lint-unsafe-doc.md](rules/lint-unsafe-doc.md) |
| F33 | Obcinanie tekstu może panikować na poprawnym UTF-8 | [api-extension-trait.md](rules/api-extension-trait.md) |
| F34 | Zamiana makra double na funkcję zmienia wynik z 42 na 441 | [macro-prefer-functions.md](rules/macro-prefer-functions.md) |
| F35 | parse_macro_input! nie działa w pomocniku zwracającym Result | [macro-proc-error-spans.md](rules/macro-proc-error-spans.md) |
| F36 | Wzorzec Partially Sealed nie pozwala użytkownikowi nadpisać name | [api-sealed-trait.md](rules/api-sealed-trait.md) |
| F37 | Konfiguracja unused_must_use w sekcji clippy nie wymusza błędu | [api-must-use.md](rules/api-must-use.md) |
| F38 | Usunięcie const z publicznego const fn łamie używający go kod | [const-fn.md](rules/const-fn.md) |
| F39 | Dzielenie chronione tylko przed zerem nadal panikuje dla MIN / -1 | [doc-panics-section.md](rules/doc-panics-section.md), [err-result-over-panic.md](rules/err-result-over-panic.md), [type-result-fallible.md](rules/type-result-fallible.md) |
| F40 | Konwersja identyfikatora do i64 zmienia duże dodatnie ID w ujemne | [type-newtype-ids.md](rules/type-newtype-ids.md) |
| F41 | Dziedziczenia lintów workspace nie można łączyć z lokalnym nadpisaniem w Cargo.toml | [lint-workspace-lints.md](rules/lint-workspace-lints.md) |
| F42 | should_panic nie obsługuje testu zwracającego Result | [test-should-panic.md](rules/test-should-panic.md) |
| F43 | Wejście tests/api/mod.rs nie jest automatycznie uruchamianym testem integracyjnym | [test-integration-dir.md](rules/test-integration-dir.md) |
| F44 | INSTA_UPDATE=unseen akceptuje nowe snapshoty zamiast je odrzucać w CI | [test-snapshot-testing.md](rules/test-snapshot-testing.md) |
| F45 | Łańcuch returning ustawia ostatnią odpowiedź zamiast sekwencji 1,2,3 | [test-mockall-mocking.md](rules/test-mockall-mocking.md) |
| F46 | Clippy nie przyjmuje warn=[...] w clippy.toml | [lint-warn-suspicious.md](rules/lint-warn-suspicious.md), [proj-mod-rs-dir.md](rules/proj-mod-rs-dir.md) |
| F47 | Grupa pedantic i jej wyjątki bez priority powodują błąd Clippy | [lint-cargo-metadata.md](rules/lint-cargo-metadata.md), [lint-pedantic-selective.md](rules/lint-pedantic-selective.md) |
| F48 | Klonowanie Arc/Rc przed await nie zapewnia Send, a pożyczony slice nie odbiera go automatycznie | [async-clone-before-await.md](rules/async-clone-before-await.md) |
| F49 | Runtime przeznaczony dla I/O nie włącza sterowników I/O ani czasu | [async-tokio-runtime.md](rules/async-tokio-runtime.md) |
| F50 | Zerowy chunk_size uniemożliwia zakończenie process_in_chunks | [perf-drain-reuse.md](rules/perf-drain-reuse.md) |
| F51 | Debug błędu nie gwarantuje pełnego łańcucha source | [obs-error-chain.md](rules/obs-error-chain.md) |
| F52 | Ponowny eksport makra w tym samym korzeniu powoduje E0255 | [macro-export-crate-path.md](rules/macro-export-crate-path.md) |
| F53 | Domyślna liczba ponowień wynosi zero zamiast opisanych trzech | [api-builder-pattern.md](rules/api-builder-pattern.md) |
| F54 | Opis must_use myli atrybut typu Result z metodami Option | [api-builder-must-use.md](rules/api-builder-must-use.md), [api-must-use.md](rules/api-must-use.md) |
| F55 | Ignorowanie konsumującego buildera nie pozwala wysłać starej konfiguracji | [api-builder-must-use.md](rules/api-builder-must-use.md) |
| F56 | move nie wyłącza precyzyjnego przechwytywania pól w edition 2021+ | [closure-disjoint-capture.md](rules/closure-disjoint-capture.md) |
| F57 | Pokazane nieprzechwytujące closures nie wymagają Box<dyn Fn> | [closure-impl-fn-return.md](rules/closure-impl-fn-return.md) |
| F58 | Edition 2024 nie zakazuje deklaracji ani odczytu wartości static mut | [const-vs-static.md](rules/const-vs-static.md) |
| F59 | str i String nie koercjonują automatycznie do Path | [own-slice-over-vec.md](rules/own-slice-over-vec.md) |
| F60 | Przykład deref coercion pożycza Vec po skonsumowaniu go | [own-slice-over-vec.md](rules/own-slice-over-vec.md) |
| F61 | all-features nie uruchamia wszystkich kombinacji cech | [api-serde-optional.md](rules/api-serde-optional.md) |
| F62 | Const generic defaults ustabilizowano w 1.59, nie 1.65 | [const-generics.md](rules/const-generics.md) |
| F63 | Diverging return -> ! jest starszy niż Rust1.41 | [type-never-diverge.md](rules/type-never-diverge.md) |
| F64 | VecDeque nie spełnia wymagania O(1) split/splice w dowolnym miejscu | [coll-seq-choice.md](rules/coll-seq-choice.md) |
| F65 | Bezwzględne zalecenie derive Debug pomija ukrywanie sekretów | [api-common-traits.md](rules/api-common-traits.md), [type-display-vs-debug.md](rules/type-display-vs-debug.md) |
| F66 | Komentarz mylnie wymaga deklaracji static lub literału do uzyskania &'static str | [const-vs-static.md](rules/const-vs-static.md) |
| F67 | Samo impl Into nie narzuca dodatkowego kosztu wywołania | [api-impl-into.md](rules/api-impl-into.md) |
| F68 | Przykład Cow deklaruje Option, lecz zwraca nieopakowane Cow | [own-borrow-over-clone.md](rules/own-borrow-over-clone.md) |
| F69 | Przykład parsowania granicznego zwraca () zamiast Result<Response, Error> | [api-parse-dont-validate.md](rules/api-parse-dont-validate.md) |
| F70 | Samo utworzenie HashMap nie wymaga Hash ani Eq klucza | [api-common-traits.md](rules/api-common-traits.md) |
| F71 | Przykłady konfiguracji stable rustfmt zawierają ignorowane opcje nightly | [lint-rustfmt-check.md](rules/lint-rustfmt-check.md) |
| F72 | EnvGuard usuwa pierwotną zmienną środowiskową o wartości non-Unicode | [test-fixture-raii.md](rules/test-fixture-raii.md) |
| F73 | Domyślny tokio::test korzysta z current_thread | [test-tokio-async.md](rules/test-tokio-async.md) |
| F74 | Znaczenie lintów mod_module_files i self_named_module_files jest odwrócone | [proj-mod-rs-dir.md](rules/proj-mod-rs-dir.md) |
| F75 | Autocfg pyta o niekompletny typ BTreeMap i stale zgłasza brak wsparcia | [proj-build-rs-minimal.md](rules/proj-build-rs-minimal.md) |
| F76 | no_run nie nadaje przykładowi kontekstu async | [doc-hidden-setup.md](rules/doc-hidden-setup.md) |
| F77 | Sam operator ? nie tworzy automatycznie wrappera doctestu zwracającego Result | [doc-link-types.md](rules/doc-link-types.md), [doc-module-inner.md](rules/doc-module-inner.md), [doc-question-mark.md](rules/doc-question-mark.md) |
| F78 | Przykład no_std wymaga jawnego importu crate alloc | [proj-feature-additive.md](rules/proj-feature-additive.md) |
| F79 | Puste vec![] nie wykonuje dodatkowej alokacji względem Vec::new | [lint-warn-perf.md](rules/lint-warn-perf.md) |
| F80 | Funkcja oznaczona #[test] nie trafia do zwykłego release bez cfg(test) | [test-cfg-test-module.md](rules/test-cfg-test-module.md) |
| F81 | Jawny import z crate nie odbiera potomnemu modułowi dostępu do prywatnych elementów | [test-use-super.md](rules/test-use-super.md) |
| F82 | Cargo automatycznie wykrywa README.md bez pola readme | [doc-crate-readme.md](rules/doc-crate-readme.md) |
| F83 | Build script bez rerun-if nie uruchamia się bezwarunkowo przy każdym buildzie | [proj-build-rs-minimal.md](rules/proj-build-rs-minimal.md) |
| F84 | Przykład standardowej biblioteki używa nieistniejącego std::io::IoError | [name-acronym-word.md](rules/name-acronym-word.md) |
| F85 | Przykłady konwersji kolekcji mają niezgodne adnotacje typów wyniku | [name-into-ownership.md](rules/name-into-ownership.md), [name-to-expensive.md](rules/name-to-expensive.md) |
| F86 | Doctest get porównuje Option<&T> z &T | [doc-panics-section.md](rules/doc-panics-section.md) |
| F87 | Opis secrecy nie odpowiada przypiętej wersji i błędnie obiecuje Display | [obs-no-sensitive-data.md](rules/obs-no-sensitive-data.md) |
| F88 | thread::spawn zwraca JoinHandle, więc przykład z expect nie kompiluje się | [anti-expect-lazy.md](rules/anti-expect-lazy.md) |
| F89 | Końcowe ? w load_user usuwa Result wymagany przez sygnaturę | [err-lowercase-msg.md](rules/err-lowercase-msg.md) |
| F90 | Indeksowanie nie wymusza bounds checks i nie uniemożliwia SIMD | [anti-index-over-iter.md](rules/anti-index-over-iter.md), [perf-iter-over-index.md](rules/perf-iter-over-index.md) |
| F91 | Generyczne funkcje mogą być inlinowane między crate bez inline i LTO | [opt-inline-always-rare.md](rules/opt-inline-always-rare.md), [opt-inline-small.md](rules/opt-inline-small.md) |
| F92 | collect nie zawsze tworzy nową alokację; pokazany pipeline może je wszystkie ponownie wykorzystać | [anti-collect-intermediate.md](rules/anti-collect-intermediate.md), [perf-collect-once.md](rules/perf-collect-once.md), [perf-iter-lazy.md](rules/perf-iter-lazy.md) |
| F93 | BufRead::lines tworzy osobny String dla każdej linii | [perf-io-buffering.md](rules/perf-io-buffering.md) |
| F94 | CompactString mieści 24 bajty inline na celu 64-bitowym, a SmartString 23 | [mem-compact-string.md](rules/mem-compact-string.md) |
| F95 | Porównanie size_of SmartString pomija wymagany parametr Mode | [mem-compact-string.md](rules/mem-compact-string.md) |
| F96 | Opis ThinVec błędnie neguje NPO Vec i nazywa pusty ThinVec null | [mem-thinvec.md](rules/mem-thinvec.md) |
| F97 | rename_all lowercase i UPPERCASE nie usuwają podkreśleń z nazw pól | [serde-rename-all.md](rules/serde-rename-all.md) |
| F98 | Internally tagged enum dopuszcza także warianty unit | [serde-enum-representation.md](rules/serde-enum-representation.md) |
| F99 | log obsługuje structured fields przez feature kv | [obs-tracing-over-log.md](rules/obs-tracing-over-log.md) |
| F100 | Feature do mostu log w tracing-subscriber nazywa się tracing-log | [obs-tracing-over-log.md](rules/obs-tracing-over-log.md) |
| F101 | try_join anuluje bezpośrednie future przez synchroniczne zniszczenie | [async-join-parallel.md](rules/async-join-parallel.md) |
