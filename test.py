def test_1(rel_, any_shared_,leading_edges, exposed_edges, same_axis):
    if rel_ == "WINDWARD":
        print("wind_relation.value:WINDWARD")
        if any_shared_:
            print("--> any_shared_ ise DUOPITCH", "HIPPED")
        else:
            print("--> any_shared_ değil ise MONOPITCH")

        print("FGH", leading_edges,
                "kenarlar e/10 offset et ve FG olarak işaretle. poligonun kalan kısmı H")
        print("Bakılacak tablo:", 0)

        

    elif rel_ == "LEEWARD":
        print("wind_relation.value: LEEWARD")
        if any_shared_:
            print("--> any_shared_ ise DUOPITCH", "HIPPED")
            print("DUOPITCH veya HIPPED çatı tipi farketmiyor ama cpe değerlerini kontrol et")
            print("DUOPITCH için JI HIPPED için KJI.. önce türbülans alanı için "
                    "leading_edges kenarları e/10 offset yap",
                    f"edge indexes:{leading_edges}", "K, diğer exposed kenarlar:",
                    f"edge indexes:{exposed_edges}", "J olur. yüzeyin geri kalanı her zaman I")

            
        else:
            print("--> any_shared_ değil ise MONOPITCH")
            print("Bakılacak tablo:", 180)
            print("FGH", f"edge indexes:{leading_edges}",
                    "kenarlar e/10 offset et ve FG olarak işaretle. "
                    "alçak saçak tarafı Fl, yüksek saçak tarafı Fu poligonun kalan kısmı H")

    elif rel_ == "PARALLEL":
        print("wind_relation.value: PARALLEL")
        if any_shared_:
            if same_axis:
                print("--> any_shared_ ise ve same_axis ise DUOPITCH")
                print("Bakılacak tablo:", 90)
                print("FGHI", f"edge indexes:{leading_edges}", "kenarlar e/10 offset et ve FG olarak işaretle.")
                print("FG Bölgesi aynı akstaki diğer kenara uzayacak.",
                        f"edge indexes:{leading_edges} alçak kot e/4 mesafede F kalan bölge G")
                print("poligonun kalan kısmı e/2 ye kadar H sonrası I")
            else:
                print("--> any_shared_ ise ve same_axis değil ise HIPPED")
                print("Bakılacak tablo:", 0)
                print("LMN", f"edge indexes:{leading_edges}",
                        "kenarlar e/10 offset et ve L olarak işaretle. "
                        "poligonun kalan kısmı e/2 ye kadar M sonrası N")
        else:
            print("--> any_shared_ değil ise MONOPITCH")
            print("Bakılacak tablo:", 90)
            print("FGH", f"edge indexes:{leading_edges}",
                    "kenarlar e/10 offset et ve FG olarak işaretle. "
                    "poligonun kalan kısmı e/2 ye kadar H sonrası I")


test_1("WINDWARD", True, [2],[2], False)
test_1("WINDWARD", True, [2],[2], True)

test_1("WINDWARD", False, [2],[2], False)
test_1("WINDWARD", False, [2],[2], True)

test_1("LEEWARD", False, [2],[2], False)
test_1("LEEWARD", False, [2],[2], True)

test_1("LEEWARD", True, [2],[2], False)
test_1("LEEWARD", True, [2],[2], True)

test_1("PARALLEL", False, [2],[2], False)
test_1("PARALLEL", False, [2],[2], True)

test_1("PARALLEL", True, [2],[2], False)
test_1("PARALLEL", True, [2],[2], True)