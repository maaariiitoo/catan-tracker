// Plugin de BepInEx que apunta la VERDAD de cada partida: que hay en cada
// vertice, de quien es, que sale en los dados y que hace cada jugador.
//
// SOLO INFORMACION PUBLICA. Todo lo que se escribe aqui es algo que ven
// todos los que estan en la mesa: el tablero, los dados, los colores, las
// acciones, los puntos VISIBLES, que se ha intercambiado en cada comercio, a
// quien se ha robado y que carta se ha jugado.
//
// Lo que NO se apunta, y en los dos casos a proposito:
//   - las manos de nadie, ni los puntos escondidos de las cartas de
//     desarrollo (ver BuscarReglaDePuntos)
//   - QUE carta se ha llevado un robo, y las cartas que alguien descarta al
//     salir un 7 (ver Detalle, que lee una lista blanca justo para no
//     arrastrarlas sin querer)
//
// Para que sirve: el tracker deduce todo eso mirando pixeles y no hay forma
// de saber cuanto acierta. Con esto, jugando contra la IA, se genera un
// fichero con el estado exacto en cada momento; despues se compara con lo
// que vio la vision, vertice a vertice, y por fin se sabe de que se puede
// uno fiar. Y esas mismas anotaciones son las etiquetas que necesitaria una
// red neuronal, escritas por el juego en vez de a mano.
//
// Como se engancha: TODAS las acciones del juego (construir un poblado,
// tirar los dados, repartir recursos, robar...) tienen la misma firma
//     void Apply(CommonGameState gameState, CommonGameActionState actionState)
// asi que con una sola intercepcion se cubren las 279 acciones que tiene
// Catan.GameLogic.Actions, y ademas se sabe CUAL ha sido por el nombre de
// la clase.
//
// No cambia nada del juego: solo mira y escribe un fichero. El postfix se
// ejecuta despues de que la accion ya haya surtido efecto.
//
// Escrito para el compilador de .NET Framework (C# 5): sin interpolacion de
// cadenas ni miembros con cuerpo de expresion.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Text;
using BepInEx;
using HarmonyLib;

namespace CatanVerdad
{
    [BepInPlugin("mario.catan.verdad", "Catan Verdad", "1.0.0")]
    public class Plugin : BaseUnityPlugin
    {
        internal static object Candado = new object();
        internal static StreamWriter Salida;
        internal static long Numero;
        internal static BepInEx.Logging.ManualLogSource Registro;
        internal static bool EsquemaVolcado;

        // Una partida, un fichero. Antes se abria uno en Awake y ya, o sea
        // UNO POR ARRANQUE DEL JUEGO: jugando tres seguidas sin cerrar Catan,
        // las tres caian en el mismo fichero. Y eso no falla ruidosamente --
        // falla en silencio, que es peor: red/dataset.py se alinea con el
        // ULTIMO estado apuntado, asi que le habria pegado el tablero de la
        // tercera partida a las fotos de la primera. Etiquetas mal puestas
        // que entrenan igual de bien y no valen para nada.
        internal static bool PartidaEnCurso;
        internal static long UltimoInicioMs;

        private static bool Enganchado;

        private void Awake()
        {
            Registro = Logger;
            AbrirFichero();

            // BUG REAL, y de los que no se notan: Awake corre MUY pronto, y
            // Assembly-CSharp (donde vive el juego) puede no estar cargada
            // todavia en el AppDomain. La version anterior, si no la
            // encontraba, se quedaba con la assembly de BepInEx como si fuera
            // la del juego -- ahi no hay ningun Catan.GameLogic.Actions, asi
            // que recorria cero tipos, enganchaba cero y no se quejaba de
            // nada. En el log solo salia "acciones enganchadas: 0" y el
            // fichero de verdad se quedaba vacio para siempre.
            //
            // Ahora: se intenta ya, y si todavia no esta, se espera a que el
            // propio AppDomain avise de que la ha cargado.
            if (!Enganchar())
            {
                Registro.LogInfo("Assembly-CSharp todavia no esta cargada; " +
                                 "se enganchara en cuanto lo este.");
                AppDomain.CurrentDomain.AssemblyLoad += CuandoCargueUnaAssembly;
            }
        }

        private static void CuandoCargueUnaAssembly(object emisor, AssemblyLoadEventArgs e)
        {
            if (Enganchado) return;
            if (e.LoadedAssembly == null) return;
            if (e.LoadedAssembly.GetName().Name != "Assembly-CSharp") return;
            Enganchar();
        }

        private static Assembly BuscarAssembly(string nombre)
        {
            foreach (Assembly a in AppDomain.CurrentDomain.GetAssemblies())
            {
                if (a.GetName().Name == nombre) return a;
            }
            try { return Assembly.Load(nombre); }
            catch (Exception) { return null; }
        }

        // Devuelve true si ya ha enganchado algo. Escribe en el log TODOS los
        // numeros del camino (tipos vistos, tipos en el espacio de nombres,
        // metodos Apply encontrados, enganchados) para que la proxima vez que
        // falle se vea en que paso se rompe, en vez de tener que deducirlo.
        private static bool Enganchar()
        {
            if (Enganchado) return true;

            Assembly juego = BuscarAssembly("Assembly-CSharp");
            if (juego == null) return false;

            Type[] tipos;
            try { tipos = juego.GetTypes(); }
            catch (ReflectionTypeLoadException e) { tipos = e.Types; }

            var harmony = new Harmony("mario.catan.verdad");
            MethodInfo postfix = typeof(Espia).GetMethod("Despues",
                BindingFlags.Static | BindingFlags.NonPublic);

            int enElEspacio = 0, conApply = 0, enganchadas = 0, fallos = 0;
            foreach (Type t in tipos)
            {
                if (t == null || t.Namespace == null) continue;
                if (!t.Namespace.StartsWith("Catan.GameLogic.Actions")) continue;
                enElEspacio++;

                // Verificado sobre el .dll con Mono.Cecil: 276 tipos aqui, 232
                // declaran Apply, y los 232 son
                //     public STATIC void Apply(CommonGameState, CommonGameActionState)
                //
                // Lo de STATIC no es un detalle. Aqui se buscaba solo con
                // BindingFlags.Instance, y entonces GetMethods no devuelve
                // ninguno: el log decia "en Catan.GameLogic.Actions: 282, con
                // Apply: 0", que parecia que el juego hubiera cambiado cuando
                // lo que pasaba es que se estaba mirando donde no era. Las
                // clases de accion son contenedores abstractos sin instancia
                // -- por eso las 232 "comparten firma".
                //
                // Se busca por nombre y numero de parametros y no por tipos:
                // pedir la firma exacta obligaria a referenciar las clases del
                // juego al compilar, y entonces el plugin dejaria de valer en
                // cuanto el juego se actualizara y cambiara una de ellas.
                MethodInfo m = null;
                foreach (MethodInfo cand in t.GetMethods(BindingFlags.Public |
                    BindingFlags.NonPublic | BindingFlags.Static |
                    BindingFlags.Instance | BindingFlags.DeclaredOnly))
                {
                    if (cand.Name == "Apply" && cand.GetParameters().Length == 2)
                    {
                        m = cand;
                        break;
                    }
                }
                if (m == null || m.IsAbstract || m.ContainsGenericParameters) continue;
                conApply++;
                try
                {
                    harmony.Patch(m, null, new HarmonyMethod(postfix));
                    enganchadas++;
                }
                catch (Exception ex)
                {
                    fallos++;
                    if (fallos <= 5)
                        Registro.LogWarning("no se pudo enganchar " + t.FullName + ": " + ex.Message);
                }
            }

            Registro.LogInfo("assembly: " + juego.GetName().Name +
                             "  tipos: " + tipos.Length +
                             "  en Catan.GameLogic.Actions: " + enElEspacio +
                             "  con Apply: " + conApply);
            Registro.LogInfo("acciones enganchadas: " + enganchadas);
            if (enganchadas == 0)
            {
                Registro.LogWarning("CERO enganches: no se va a apuntar nada. Si " +
                                    "'en Catan.GameLogic.Actions' es 0, el juego ha " +
                                    "cambiado el espacio de nombres.");
                return false;
            }
            Enganchado = true;
            return true;
        }

        internal static void AbrirFichero()
        {
            string carpeta = Path.Combine(Paths.GameRootPath, "verdad_catan");
            Directory.CreateDirectory(carpeta);
            string nombre = "partida_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".jsonl";
            string ruta = Path.Combine(carpeta, nombre);
            lock (Candado)
            {
                if (Salida != null) { Salida.Flush(); Salida.Close(); }
                Salida = new StreamWriter(ruta, false, new UTF8Encoding(false));
                Salida.AutoFlush = true;
                Numero = 0;
                // El esquema se vuelve a volcar en cada fichero. Si no, el
                // segundo se quedaria sin la tabla de colores y las piezas
                // de esa partida no se podrian atribuir a nadie -- que es
                // justo el dato que sirve de una partida a otra.
                EsquemaVolcado = false;
                PartidaEnCurso = false;
            }
            if (Registro != null) Registro.LogInfo("Apuntando la verdad en " + ruta);
        }

        private void OnDestroy()
        {
            lock (Candado)
            {
                if (Salida != null) { Salida.Flush(); Salida.Close(); Salida = null; }
            }
        }
    }

    internal static class Espia
    {
        // __0 = el primer parametro de Apply, o sea el estado del juego. Se
        // pide como object para no tener que referenciar los tipos del juego
        // al compilar: asi el plugin sigue valiendo si el juego se actualiza y
        // cambia alguna clase.
        //
        // __originalMethod es el metodo parcheado, y de el sale QUE accion ha
        // sido (su clase se llama CatanBase_BuildSettlement_GameAction y
        // demas). Antes esto se sacaba de __instance, y __instance NO EXISTE
        // en un metodo estatico: Harmony habria reventado al parchear. Los
        // 232 Apply son estaticos, asi que no hay ninguna instancia de la que
        // preguntar.
        private static void Despues(MethodBase __originalMethod, object __0, object __1)
        {
            try { Apuntar(__originalMethod, __0, __1); }
            catch (Exception e)
            {
                if (Plugin.Registro != null) Plugin.Registro.LogWarning("fallo apuntando: " + e.Message);
            }
        }

        private static void Apuntar(MethodBase accion, object estadoComun, object estadoAccion)
        {
            if (estadoComun == null) return;
            object catan = Campo(estadoComun, "CatanGameState");
            if (catan == null) return;
            object tablero = Campo(catan, "Board");
            object partida = Campo(catan, "Match");
            if (tablero == null) return;

            string nombreAccion = "?";
            if (accion != null && accion.DeclaringType != null)
                nombreAccion = accion.DeclaringType.Name;

            // Cambiar de fichero cuando empieza otra partida.
            //
            // Estas dos acciones salen una vez por partida y son las
            // primeras de todas. La guarda de tiempo hace falta por dos
            // motivos, los dos medidos sobre las partidas grabadas:
            //
            //   - el juego ejecuta CADA accion cinco veces seguidas, dentro
            //     de 18 ms. Sin guarda, la segunda copia abriria otro
            //     fichero y saldrian cuatro ficheros vacios por partida.
            //   - de SetupPlayerInventory a StartGame pasan 0,3 s, asi que
            //     las dos marcas de la MISMA partida caen juntisimas.
            //
            // Entre una partida y la siguiente pasan 19-22 minutos. Treinta
            // segundos separa las dos cosas con muchisimo margen.
            if (nombreAccion == "CatanBase_SetupPlayerInventory_GameAction" ||
                nombreAccion == "CatanBase_StartGame_GameAction")
            {
                long ahoraMs = (long)DateTime.UtcNow.Subtract(
                    new DateTime(1970, 1, 1)).TotalMilliseconds;
                if (Plugin.PartidaEnCurso && ahoraMs - Plugin.UltimoInicioMs > 30000)
                    Plugin.AbrirFichero();
                Plugin.PartidaEnCurso = true;
                Plugin.UltimoInicioMs = ahoraMs;
            }

            // La PRIMERA linea del fichero es el esquema real de las clases
            // del juego. Los nombres de los campos del jugador se pusieron
            // deduciendolos del .dll y puede que alguno no sea el que es; en
            // vez de descubrirlo partida a partida, el propio plugin apunta
            // que miembros existen de verdad y que valor tienen. Se escribe
            // una sola vez porque no cambia dentro de una partida.
            if (!Plugin.EsquemaVolcado)
            {
                Plugin.EsquemaVolcado = true;
                VolcarEsquema(estadoComun, catan, tablero, partida);
            }

            StringBuilder j = new StringBuilder(4096);
            j.Append("{");
            Par(j, "n", (++Plugin.Numero).ToString(CultureInfo.InvariantCulture), false);
            // reloj en milisegundos desde el arranque del sistema: es con lo
            // que se empareja cada captura de pantalla con su estado
            j.Append(",\"reloj_ms\":").Append(
                DateTime.UtcNow.Subtract(new DateTime(1970, 1, 1)).TotalMilliseconds
                    .ToString("F0", CultureInfo.InvariantCulture));
            j.Append(",\"accion\":\"").Append(Escapar(nombreAccion)).Append("\"");

            if (partida != null)
            {
                j.Append(",\"turno\":").Append(Entero(partida, "TurnNumber"));
                j.Append(",\"dados\":").Append(ListaDeEnteros(Campo(partida, "DiceValues")));
                j.Append(",\"camino_mas_largo\":").Append(Entero(partida, "LongestRoadPlayerId"));
                j.Append(",\"mayor_ejercito\":").Append(Entero(partida, "LargestArmyPlayerId"));
            }

            j.Append(",\"casillas\":").Append(Casillas(tablero));
            j.Append(",\"puertos\":").Append(Puertos(tablero));
            j.Append(",\"edificios\":").Append(Piezas(tablero, "GamePiecesBuildings"));
            j.Append(",\"carreteras\":").Append(Piezas(tablero, "GamePiecesPath"));
            string ladron = Ladron(catan, tablero);
            j.Append(",\"ladron\":").Append(ladron);
            // Una sola vez, y solo si no se ha encontrado: los NOMBRES de
            // los campos del tablero que suenan a ladron. Nombres, no
            // contenidos -- es lo justo para saber donde mirar la proxima
            // vez sin volcar nada.
            if (ladron == "null" && !_ladronBuscado)
            {
                _ladronBuscado = true;
                j.Append(",\"ladron_donde_buscar\":")
                 .Append(NombresQueSuenanA(tablero, "robber"));
            }
            j.Append(",\"extras\":").Append(Extras(tablero));
            j.Append(",\"jugador_activo\":").Append(Entero(estadoComun, "activePlayerId"));
            // Quien ha hecho ESTA accion, que no siempre es el del turno y
            // ademas es fiable: `activePlayerId` sale -1 en tres de las cinco
            // copias que el juego escribe de cada accion, y este no.
            j.Append(",\"accion_de\":").Append(Entero(estadoAccion, "PlayerId"));
            string detalle = Detalle(accion, estadoAccion);
            if (detalle != null) j.Append(",\"detalle\":").Append(detalle);
            j.Append(",\"jugadores\":").Append(Jugadores(
                estadoComun, catan,
                nombreAccion == "CatanBase_WinGame_GameAction"));
            j.Append("}");

            lock (Plugin.Candado)
            {
                if (Plugin.Salida != null) Plugin.Salida.WriteLine(j.ToString());
            }
        }

        // --- el detalle de la accion ------------------------------------
        // El segundo parametro de Apply (CommonGameActionState) lleva lo que
        // el estado del juego no dice: QUE se ha intercambiado en un
        // comercio, A QUIEN se ha robado, QUE carta se ha jugado.
        //
        // Los nombres no estan adivinados, salen de leer Assembly-CSharp.dll:
        //
        //   CommonGameActionState.CatanGameActionState
        //     .AsTradeFinish   -> Trade_Finish_GameActionState
        //                         OffererPlayerId, AcceptedPlayerId,
        //                         Offer.Give, Offer.Want, Is3to2Bank, Is2to1Bank
        //     .AsTradeInit     -> Trade_Bank_Init_GameActionState
        //                         Ratio, Offer.Give, Offer.Want
        //     .AsSelectAblePlayers -> SelectPlayer_GameActionState
        //                         PlayersList, SelectedPlayer
        //     .AsPlayCard      -> Base_PlayCard_GameActionState.Card
        //     .AsResourceTypeToChoose -> ResourceTypeToChoose_GameActionState
        //                         ChosenResourceType
        //     .AsResourcesFromPlayers -> ResourcesFromPlayers_GameActionState
        //                         Resources: Dictionary<int, CardBundleModel>
        //                           (la clave es el ID del jugador)
        //                         ChosenResourceType
        //   CardBundleModel.Resources -> List<GameCard>, y GameCard tiene
        //   BaseRes (el recurso) y Amount.
        //
        // COMO SE LEEN ESTOS NOMBRES, que no hace falta jugar para saberlos:
        // BepInEx trae Mono.Cecil en BepInEx\core, asi que el ensamblado se
        // puede abrir y recorrer sin arrancar el juego --
        //
        //   Add-Type -Path "...\BepInEx\core\Mono.Cecil.dll"
        //   $asm = [Mono.Cecil.AssemblyDefinition]::ReadAssembly(
        //            "...\CatanUniverse_Data\Managed\Assembly-CSharp.dll")
        //   $asm.MainModule.GetTypes() | ... .Fields
        //
        // -- y salen los campos con su tipo. Se hizo al reves con los puertos
        // (escribir, jugar, ver que llegaba vacio) y costo dos partidas.
        //
        // ESTO ES UNA LISTA BLANCA, Y ES A PROPOSITO. Al lado de estos
        // campos, en la MISMA clase, estan estos otros:
        //
        //     .AsRobbedResources -> las cartas que alguien descarta al salir
        //                           un 7. Nadie mas las ve.
        //
        // Un volcador generico que recorriera CatanGameActionState entero
        // los sacaria tambien, y nadie se enteraria hasta mucho despues. Por
        // eso se leen uno a uno los que se quieren y no se recorre nada.
        //
        // Lo que hay aqui es todo publico: un comercio lo ven los dos que lo
        // hacen y lo anuncia el juego, a quien has robado se ve, y la carta
        // que juegas la enseñas al jugarla. Lo que NO se puede saber es QUE
        // carta te has llevado en el robo -- eso no lo ve nadie y no esta.
        private static string Detalle(MethodBase accion, object estadoAccion)
        {
            if (estadoAccion == null) return null;
            object c = Campo(estadoAccion, "CatanGameActionState");
            if (c == null) return null;

            StringBuilder s = new StringBuilder(256);
            s.Append("{");
            bool alguno = false;

            object fin = Campo(c, "AsTradeFinish");
            if (fin != null)
            {
                object oferta = Campo(fin, "Offer");
                s.Append("\"comercio\":{");
                s.Append("\"ofrece\":").Append(Entero(fin, "OffererPlayerId"));
                s.Append(",\"acepta\":").Append(Entero(fin, "AcceptedPlayerId"));
                s.Append(",\"da\":").Append(Cartas(Campo(oferta, "Give")));
                s.Append(",\"pide\":").Append(Cartas(Campo(oferta, "Want")));
                s.Append(",\"banco_3a2\":").Append(Booleano(fin, "Is3to2Bank"));
                s.Append(",\"banco_2a1\":").Append(Booleano(fin, "Is2to1Bank"));
                s.Append("}");
                alguno = true;
            }

            object ini = Campo(c, "AsTradeInit");
            if (ini != null)
            {
                object oferta = Campo(ini, "Offer");
                if (alguno) s.Append(",");
                s.Append("\"comercio_banco\":{");
                s.Append("\"da\":").Append(Cartas(Campo(oferta, "Give")));
                s.Append(",\"pide\":").Append(Cartas(Campo(oferta, "Want")));
                s.Append(",\"cambio\":").Append(Cartas(Campo(ini, "Ratio")));
                s.Append("}");
                alguno = true;
            }

            object sel = Campo(c, "AsSelectAblePlayers");
            if (sel != null)
            {
                if (alguno) s.Append(",");
                s.Append("\"robado_a\":").Append(Entero(sel, "SelectedPlayer"));
                s.Append(",\"podia_robar_a\":").Append(ListaDeEnteros(Campo(sel, "PlayersList")));
                alguno = true;
            }

            object carta = Campo(c, "AsPlayCard");
            if (carta != null)
            {
                object g = Campo(carta, "Card");
                if (alguno) s.Append(",");
                s.Append("\"carta\":{\"tipo\":\"").Append(Escapar(Texto(Campo(g, "Type"))));
                s.Append("\",\"desarrollo\":\"")
                 .Append(Escapar(Texto(Campo(Campo(g, "AsDevelopmentCard"), "Type"))));
                s.Append("\"}");
                alguno = true;
            }

            // El monopolio: quien lo tira ya se sabe (accion_de) y QUE recurso
            // pide tambien (AsResourceTypeToChoose, mas abajo). Lo que faltaba
            // es cuantas cartas suelta cada uno, y eso esta aqui.
            //
            // Es informacion PUBLICA: cuando alguien juega un monopolio, la
            // mesa entera ve lo que entrega cada jugador. No es como el robo
            // del ladron, donde nadie ve que carta se lleva.
            //
            // Se lee campo a campo y con nombres, como todo lo demas de aqui.
            // El primer intento fue volcar el objeto entero por reflexion
            // porque no se sabia que forma tenia; leyendo Assembly-CSharp.dll
            // con Mono.Cecil resulto que se sabe perfectamente:
            //
            //   AsResourcesFromPlayers -> ResourcesFromPlayers_GameActionState
            //       .Resources          Dictionary<int, CardBundleModel>
            //                           la clave es el ID del jugador
            //       .ChosenResourceType BaseResourceType?
            //
            // Y CardBundleModel es el MISMO tipo que ya se lee en los
            // comercios, asi que `Cartas()` vale tal cual. Un volcado
            // generico habria salido con los nombres del juego y una forma
            // distinta a la del resto del fichero, y encima habria que
            // adivinarla luego al importar.
            //
            // Lo que NO se puede hacer nunca es volcar `c` entero, porque en
            // esa misma clase esta `AsRobbedResources` -- las cartas que se
            // descartan al salir un 7, que son de la mano de cada uno y no
            // las ve nadie.
            object monopolio = Campo(c, "AsResourcesFromPlayers");
            if (monopolio != null)
            {
                if (alguno) s.Append(",");
                s.Append("\"monopolio\":{");
                s.Append("\"recurso\":\"")
                 .Append(Escapar(Texto(Campo(monopolio, "ChosenResourceType"))))
                 .Append("\",\"de\":")
                 .Append(PorJugador(Campo(monopolio, "Resources")));
                // Y el objeto tal cual, UNA temporada. Los nombres de arriba
                // estan leidos del .dll, no adivinados, pero que un campo
                // exista no dice que este relleno en el momento en que se
                // mira -- es exactamente lo que paso con los puertos, donde
                // `HarborType` existia y venia vacio. Con esto, si `de` sale
                // vacio se ve POR QUE en la misma grabacion, en vez de perder
                // otra partida. Se quita en cuanto una lo confirme.
                s.Append(",\"crudo\":").Append(Volcado(monopolio, 4));
                s.Append("}");
                alguno = true;
            }

            object elegido = Campo(c, "AsResourceTypeToChoose");
            if (elegido != null)
            {
                if (alguno) s.Append(",");
                s.Append("\"recurso_elegido\":\"")
                 .Append(Escapar(Texto(Campo(elegido, "ChosenResourceType")))).Append("\"");
                alguno = true;
            }

            // Y los otros cincuenta y siete: cuales han disparado, sin
            // mirar lo que llevan dentro.
            string pres = Presentes(c);
            if (pres != "[]")
            {
                if (alguno) s.Append(",");
                s.Append("\"presentes\":").Append(pres);
                alguno = true;
            }

            if (!alguno) return null;
            return s.Append("}").ToString();
        }

        // LOS 63 ACCESORES DE `CatanGameActionState`, contemplados enteros.
        //
        // Arriba se leen SEIS: el comercio, la banca, a quien se roba, que
        // carta se juega, el reparto del monopolio y el recurso elegido. Los
        // otros cincuenta y siete son de las expansiones que trae Catan
        // Universe -- barcos, campos de oro, niebla, barbaros, cartas de
        // progreso, canales, el dragon, el Gran Canal -- y hasta ahora no
        // existian para el mod: una accion de Navegantes se apuntaba con su
        // nombre y sin nada de lo que hacia.
        //
        // AQUI NO SE VUELCA LO QUE TRAEN DENTRO, y es a proposito. La regla de
        // este fichero es no apuntar nada tapado, y de un accesor que no se ha
        // visto nunca no se puede saber si lo lleva. Dos ejemplos de la propia
        // lista: `AsSpy` es la carta de progreso que MIRA LA MANO de otro, y
        // `AsShuffleDevelopmentCards` es el ORDEN DEL MAZO -- apuntar eso
        // seria leer el futuro, que es peor que leer una mano. Volcarlos «por
        // si acaso» seria exactamente lo que este fichero no hace.
        //
        // Lo que si se apunta es CUALES han disparado. Un nombre de campo no
        // filtra nada, y el dia que se juegue a Navegantes dice exactamente
        // que payloads llevan datos y cuantas veces. Eso es lo que hace falta
        // para abrirlos uno a uno, con una grabacion delante, en vez de
        // adivinar -- que es de donde han salido todos los fallos de este
        // proyecto.
        //
        // Los de `NoMirarNunca` no se tocan ni para ver si estan.
        private static readonly string[] NoMirarNunca = {
            "AsRobbedResources",           // la carta robada y los descartes del 7
            "AsSpy",                       // mira la mano de otro
            "AsMasterMerchant",            // se lleva cartas mirando la mano
            "AsProgressCardDistribution",  // que cartas de progreso se reparten
            "AsChooseProgressCard",        // cual se eligio, y sigue tapada
            "AsProgressCardDiscard",       // que se descarta de la mano
            "AsShuffleDevelopmentCards",   // el orden del mazo: leer el futuro
            "AsShuffleProgressCards",      // idem
            "AsShuffleFogField",           // que hay bajo la niebla sin descubrir
            "AsShuffleTreasures",          // idem con los tesoros
            "AsShuffledIslands",           // idem con las islas
        };

        private static string Presentes(object c)
        {
            StringBuilder s = new StringBuilder("[");
            bool primero = true;
            Type t = c.GetType();
            while (t != null)
            {
                FieldInfo[] fs = t.GetFields(
                    BindingFlags.Public | BindingFlags.NonPublic |
                    BindingFlags.Instance | BindingFlags.DeclaredOnly);
                for (int i = 0; i < fs.Length; i++)
                {
                    string n = fs[i].Name;
                    if (n.Length < 3 || n[0] != 'A' || n[1] != 's') continue;
                    bool prohibido = false;
                    for (int k = 0; k < NoMirarNunca.Length; k++)
                        if (NoMirarNunca[k] == n) prohibido = true;
                    if (prohibido) continue;
                    object v;
                    try { v = fs[i].GetValue(c); }
                    catch (Exception) { continue; }
                    if (v == null) continue;
                    if (!primero) s.Append(",");
                    primero = false;
                    s.Append("\"").Append(Escapar(n)).Append("\"");
                }
                t = t.BaseType;
            }
            return s.Append("]").ToString();
        }

        // Un Dictionary<int, CardBundleModel> -- lo que suelta cada jugador en
        // un monopolio -- a [{"jugador":0,"cartas":[...]}, ...].
        //
        // La clave se emite como numero si de verdad lo es y como texto si no.
        // Suena a exceso de cuidado y no lo es: si un dia la clave dejara de
        // ser el ID del jugador, escribirla a pelo dejaria el JSON roto y la
        // linea entera de esa accion se perderia al importar, sin decir nada.
        private static string PorJugador(object mapa)
        {
            IDictionary d = mapa as IDictionary;
            if (d == null) return "null";
            StringBuilder s = new StringBuilder("[");
            bool primero = true;
            foreach (DictionaryEntry e in d)
            {
                if (!primero) s.Append(",");
                primero = false;
                s.Append("{\"jugador\":");
                if (e.Key is int)
                    s.Append(((int)e.Key).ToString(CultureInfo.InvariantCulture));
                else s.Append("\"").Append(Escapar(Texto(e.Key))).Append("\"");
                s.Append(",\"cartas\":").Append(Cartas(e.Value)).Append("}");
            }
            return s.Append("]").ToString();
        }

        // Un CardBundleModel -> [{"recurso":"Lumber","cantidad":2}, ...]
        private static string Cartas(object bundle)
        {
            if (bundle == null) return "null";
            IEnumerable lista = Campo(bundle, "Resources") as IEnumerable;
            if (lista == null) return "[]";
            StringBuilder s = new StringBuilder("[");
            bool primero = true;
            foreach (object g in lista)
            {
                if (g == null) continue;
                if (!primero) s.Append(",");
                primero = false;
                s.Append("{\"recurso\":\"").Append(Escapar(Texto(Campo(g, "BaseRes"))));
                s.Append("\",\"cantidad\":").Append(Entero(g, "Amount")).Append("}");
            }
            return s.Append("]").ToString();
        }

        private static string Booleano(object o, string nombre)
        {
            object v = Campo(o, nombre);
            if (v == null) return "null";
            try { return Convert.ToBoolean(v) ? "true" : "false"; }
            catch (Exception) { return "null"; }
        }

        // --- el tablero -----------------------------------------------
        // Cada casilla se identifica por su FacePosition (X,Y), que son
        // coordenadas axiales: el mismo sistema que usa vision/board_graph.py.
        private static string Casillas(object tablero)
        {
            object mapaTiles = Campo(tablero, "GamePiecesTiles");
            object mapaChips = Campo(tablero, "GamePiecesValueChip");
            Dictionary<string, string> numeros = new Dictionary<string, string>();
            IDictionary dc = mapaChips as IDictionary;
            if (dc != null)
            {
                foreach (DictionaryEntry e in dc)
                {
                    object pieza = Campo(e.Value, "Piece");
                    object chip = Campo(pieza, "AsValueChip");
                    numeros[Cara(e.Key)] = chip == null ? "null" : Entero(chip, "Value");
                }
            }

            StringBuilder s = new StringBuilder("[");
            IDictionary dt = mapaTiles as IDictionary;
            bool primero = true;
            if (dt != null)
            {
                foreach (DictionaryEntry e in dt)
                {
                    object pieza = Campo(e.Value, "Piece");
                    object tile = Campo(pieza, "AsTile");
                    string clave = Cara(e.Key);
                    if (!primero) s.Append(",");
                    primero = false;
                    s.Append("{\"pos\":").Append(clave);
                    s.Append(",\"terreno\":\"").Append(Escapar(Texto(Campo(tile, "Type")))).Append("\"");
                    s.Append(",\"numero\":").Append(numeros.ContainsKey(clave) ? numeros[clave] : "null");
                    s.Append("}");
                }
            }
            return s.Append("]").ToString();
        }

        // --- los puertos ------------------------------------------------
        // Un puerto no cambia en toda la partida, pero se escribe en cada
        // linea igual que las casillas: son cuatro objetos y asi no hay que
        // acordarse de si la primera linea de la grabacion los traia.
        //
        // Nombres verificados en Assembly-CSharp.dll antes de escribirlos, y
        // no supuestos: `GamePiecesHarbors` esta en la misma familia que
        // `GamePiecesTiles`, y la pieza tiene `AsHarbor` igual que tiene
        // `AsTile`. Que exista el nombre no dice de que TIPO es cada campo,
        // asi que lo que no esta comprobado se apunta y ya se decidira con
        // datos de verdad delante:
        //
        // Medido en la partida del 22/8 de madrugada: encuentra los NUEVE
        // puertos, y `HarborTypeValue` sale 0,1,2,3,4 una vez cada uno y 5
        // cuatro veces -- que es exactamente un tablero normal, cinco puertos
        // de recurso y cuatro genericos. Asi que ese campo es el TIPO (el
        // numero del enum), no el 2 o el 3 del cambio.
        //
        // Lo que NO salio: la posicion. Ni `Posicion(clave)` ni `Cara(clave)`
        // dieron nada, y `HarborType` como texto vino vacio. Sin la posicion
        // no se puede saber de quien es cada puerto, que es lo unico que no
        // se deduce ya de los comercios.
        //
        // Por eso ahora se vuelca el objeto entero, clave y valor: es la
        // forma de encontrar el campo bueno sin tener que jugar una partida
        // por cada nombre que se me ocurra. El tablero es publico -- lo ven
        // los cuatro jugadores -- asi que aqui volcar no expone nada.
        // LO DE ARRIBA ERA MEDIO FALSO Y SE CORRIGE AQUI. Leido el .dll con
        // Mono.Cecil, sin jugar nada:
        //
        //   BoardState.GamePiecesHarbors
        //       Dictionary<EdgePosition, PositionedGamePiece>
        //   EdgePosition { FaceA: FacePosition, FaceB: FacePosition }
        //   FacePosition { X: Int32, Y: Int32 }
        //   Harbor       { HarborTypeValue: HarborType, Direction: ... }
        //   HarborType   Lumber=0 Brick=1 Grain=2 Wool=3 Ore=4 Generic=5
        //
        // Dos fallos a la vez, y los dos invisibles:
        //
        //   1. La clave es una EdgePosition, NO una HexGridPosition. Por eso
        //      `Posicion(clave)` devolvia {"que":""} sin casillas: buscaba
        //      AsFacePos/AsEdgePos/AsCornerPos, que ahi no existen. La
        //      EdgePosition YA es la arista, con sus dos caras dentro.
        //
        //   2. `HarborType` no es un campo de Harbor: es el ENUM del campo
        //      `HarborTypeValue`. Pedirlo por ese nombre daba null siempre,
        //      de ahi el tipo vacio. Y lo que se guardaba en `cambio` como si
        //      fuera el 2:1 o el 3:1 era el RECURSO del puerto.
        //
        // CON LA ARISTA YA SE SABE DE QUIEN ES CADA PUERTO, y sin geometria
        // nueva: los dos vertices de una arista son las esquinas que tocan
        // sus dos caras, asi que un poblado tiene el puerto si entre sus tres
        // casillas estan FaceA y FaceB. El turno sale de cuando se construyo.
        private static string Puertos(object tablero)
        {
            IDictionary d = Campo(tablero, "GamePiecesHarbors") as IDictionary;
            StringBuilder s = new StringBuilder("[");
            if (d != null)
            {
                bool primero = true;
                foreach (DictionaryEntry e in d)
                {
                    object pieza = Campo(e.Value, "Piece");
                    object puerto = Campo(pieza, "AsHarbor");
                    if (!primero) s.Append(",");
                    primero = false;
                    // Las dos caras, en el MISMO formato [x,y] que las
                    // casillas de los edificios: es lo que deja cruzarlos sin
                    // traducir nada por el camino.
                    s.Append("{\"arista\":[")
                     .Append(Cara(Campo(e.Key, "FaceA"))).Append(",")
                     .Append(Cara(Campo(e.Key, "FaceB"))).Append("]");
                    s.Append(",\"tipo\":\"")
                     .Append(Escapar(Texto(Campo(puerto, "HarborTypeValue"))))
                     .Append("\"");
                    s.Append(",\"tipo_num\":").Append(Entero(puerto, "HarborTypeValue"));
                    s.Append(",\"direccion\":\"")
                     .Append(Escapar(Texto(Campo(puerto, "Direction")))).Append("\"");
                    // Y la posicion cruda una temporada, por si `FaceA`/`FaceB`
                    // llegaran sin rellenar. Es la misma red que en el
                    // monopolio, y por el mismo motivo: que un campo exista no
                    // dice que tenga algo dentro cuando se mira.
                    s.Append(",\"arista_cruda\":").Append(Volcado(e.Key, 3));
                    s.Append("}");
                }
            }
            return s.Append("]").ToString();
        }

        // TODO LO DEMAS QUE HAY EN EL TABLERO, y por que va junto en `extras`.
        //
        // El mod leia 6 de las 19 colecciones que guarda `BoardState`: las del
        // Catan basico. Las otras 13 son de las expansiones que trae Catan
        // Universe -- caballeros y murallas de Ciudades y Caballeros, el
        // pirata y la niebla de Navegantes, el mercader, los barbaros, los
        // canales, el dragon -- y se tiraban sin mas.
        //
        // No se apuntan para entenderlas hoy. El importador no sabe nada de
        // ellas y no va a saberlo hasta que haya una partida de verdad que
        // mirar: escribir ese codigo a ciegas es como se han colado todos los
        // fallos de este proyecto. Se apuntan para NO PERDERLAS. Las
        // grabaciones se guardan comprimidas (105 MB -> 0,8 MB) y la base se
        // reconstruye entera desde ellas con `--rehacer`, asi que el dia que
        // se compre una expansion, la PRIMERA partida ya estara bien grabada
        // aunque tarde meses en entenderse.
        //
        // Van dentro de `extras` para que el evento siga teniendo por fuera la
        // misma forma de siempre. Y `extras` se escribe SIEMPRE, aunque salga
        // `{}`: asi «esta partida no tenia nada de eso» se distingue de «esto
        // lo grabo un mod viejo», que no es lo mismo y a los seis meses no hay
        // manera de saber cual de las dos era.
        //
        // Dentro solo entra lo que NO esta vacio, asi que en el basico queda
        // `{}` y el fichero no crece.
        //
        // Los nombres y las FORMAS salen del ensamblado del juego leido en
        // modo solo-reflexion, no de suponer -- que es la diferencia entre
        // esto y el rato que se perdio con `HarborType`. Las siete primeras
        // son Dictionary<HexGridPosition, PositionedGamePiece>, igual que los
        // edificios; las tres sueltas son un PositionedGamePiece pelado.
        private static readonly string[] PiezasDeExpansion = {
            "GamePiecesUnits",      "unidades",     // caballeros, C y K
            "GamePiecesWall",       "murallas",     // C y K
            "GamePiecesTreasures",  "tesoros",
            "GamePiecesOvergrown",  "maleza",
            "GamePiecesCanal",      "canales",
            "GamePiecesDragon",     "dragones",
            "GamePiecesSeparators", "separadores",
        };

        private static readonly string[] SueltasDeExpansion = {
            "GamePiecesPirat",           "pirata",     // Navegantes
            "GamePiecesMerchant",        "mercader",
            "GamePiecesBarbarIndicator", "barbaros",   // C y K
        };

        private static string Extras(object tablero)
        {
            StringBuilder s = new StringBuilder("{");
            bool primero = true;
            for (int i = 0; i < PiezasDeExpansion.Length; i += 2)
            {
                IDictionary d = Campo(tablero, PiezasDeExpansion[i]) as IDictionary;
                if (d == null || d.Count == 0) continue;
                if (!primero) s.Append(",");
                primero = false;
                s.Append("\"").Append(PiezasDeExpansion[i + 1]).Append("\":")
                 .Append(Piezas(tablero, PiezasDeExpansion[i]));
            }
            for (int i = 0; i < SueltasDeExpansion.Length; i += 2)
            {
                string p = SitioDe(Campo(tablero, SueltasDeExpansion[i]),
                                   SueltasDeExpansion[i]);
                if (p == null) continue;
                if (!primero) s.Append(",");
                primero = false;
                s.Append("\"").Append(SueltasDeExpansion[i + 1]).Append("\":").Append(p);
            }
            // La niebla de Navegantes: las casillas ya descubiertas. Es una
            // lista de posiciones a secas, no de piezas.
            IList niebla = Campo(tablero, "RevealedFogTiles") as IList;
            if (niebla != null && niebla.Count > 0)
            {
                if (!primero) s.Append(",");
                primero = false;
                s.Append("\"niebla_descubierta\":").Append(Posiciones(niebla));
            }
            // Las islas, cada una con sus casillas, y lo que vale desembarcar
            // en una nueva. Juntas son de donde saldrian los puntos por isla.
            IList islas = Campo(tablero, "Islands") as IList;
            if (islas != null && islas.Count > 0)
            {
                if (!primero) s.Append(",");
                primero = false;
                s.Append("\"islas\":[");
                for (int i = 0; i < islas.Count; i++)
                {
                    if (i > 0) s.Append(",");
                    IList cas = Campo(islas[i], "GamePieces") as IList;
                    s.Append("{\"casillas\":")
                     .Append(cas == null ? "[]" : Posiciones(cas)).Append("}");
                }
                s.Append("]");
            }
            if (Campo(tablero, "VictoryPointPerIsland") != null)
            {
                if (!primero) s.Append(",");
                primero = false;
                s.Append("\"puntos_por_isla\":")
                 .Append(Entero(tablero, "VictoryPointPerIsland"));
            }
            // Casillas y fichas que la partida va anadiendo sobre la marcha:
            // clave -> cuantas. No son piezas colocadas, es el monton.
            string[] montones = { "AdditionalLandTiles", "casillas_de_mas",
                                  "AdditionalValueChips", "fichas_de_mas" };
            for (int i = 0; i < montones.Length; i += 2)
            {
                IDictionary d = Campo(tablero, montones[i]) as IDictionary;
                if (d == null || d.Count == 0) continue;
                if (!primero) s.Append(",");
                primero = false;
                s.Append("\"").Append(montones[i + 1]).Append("\":")
                 .Append(CuentaPorClave(d));
            }
            return s.Append("}").ToString();
        }

        private static string Posiciones(IList lista)
        {
            StringBuilder s = new StringBuilder("[");
            for (int i = 0; i < lista.Count; i++)
            {
                if (i > 0) s.Append(",");
                s.Append(Posicion(lista[i]));
            }
            return s.Append("]").ToString();
        }

        private static string CuentaPorClave(IDictionary d)
        {
            StringBuilder s = new StringBuilder("{");
            bool primero = true;
            foreach (DictionaryEntry e in d)
            {
                if (!primero) s.Append(",");
                primero = false;
                s.Append("\"").Append(Escapar(Texto(e.Key))).Append("\":");
                try
                {
                    s.Append(Convert.ToInt64(e.Value)
                              .ToString(CultureInfo.InvariantCulture));
                }
                catch (Exception) { s.Append("null"); }
            }
            return s.Append("}").ToString();
        }

        private static string Piezas(object tablero, string nombreCampo)
        {
            IDictionary d = Campo(tablero, nombreCampo) as IDictionary;
            StringBuilder s = new StringBuilder("[");
            if (d != null)
            {
                bool primero = true;
                foreach (DictionaryEntry e in d)
                {
                    if (!primero) s.Append(",");
                    primero = false;
                    s.Append(DescribirPieza(e.Key, e.Value));
                }
            }
            return s.Append("]").ToString();
        }

        // EL LADRON. Lo que costo, y por que ahora no es una lista de nombres
        // a ver si suena la flauta.
        //
        // En el tablero basico esta en `BoardState.GamePiecesRobber` y no
        // falla: 497 de 497 eventos en `partida_20260826_005240` y 512 de 512
        // en `partida_20260827_140346`. En el tablero de 5-6 JUGADORES ese
        // campo viene NULL en los 668 eventos de `partida_20260827_173755`
        // -- ni uno. Esa partida entro con 15 robos, CERO movimientos de
        // ladron y CERO bloqueos, y la produccion contada como si el ladron
        // no estuviera en el tablero.
        //
        // COMPROBADO YA JUGANDO, que es lo que faltaba: en
        // `partida_20260830_191015` el ladron sale en 2005 de 2005
        // anotaciones, las 2005 por `BoardQuery.GetRobberTile`, y pasa por 7
        // casillas distintas -- o sea que es la de ahora y no la inicial
        // congelada. Esa es de cuatro; el camino de seis es el `if` interno
        // del propio metodo del juego, asi que es el mismo codigo.
        //
        // La primera version de esto probaba varios nombres a ojo. Se cambio
        // por mirar el ensamblado del juego en modo solo-reflexion, que dice
        // la verdad sin adivinar nada. `Catan.GameLogic.Model.BoardState`
        // guarda al ladron en CUATRO sitios distintos, y cada uno con una
        // forma:
        //
        //   GamePiecesRobber              PositionedGamePiece
        //   GamePiecesRobbers             List<PositionedGamePiece>
        //   GamePiecesRobbersPerPlayerIdx Dictionary<int, PositionedGamePiece>
        //   GamePieces                    List<PositionedGamePiece>, TODAS
        //
        // Se prueban en ese orden y la ultima es la que no puede fallar: es
        // la lista de todas las piezas del tablero, y el ladron se reconoce
        // porque su `GamePiece.AsRobber` no es null -- que es el propio
        // discriminador del juego, no un nombre parecido.
        //
        // DOS TRAMPAS, las dos comprobadas en el ensamblado:
        //
        // 1. `GamePiecesRobbersPerPlayerIdx` es un diccionario, pero su CLAVE
        //    es el indice del jugador, NO la posicion. En `GamePiecesBuildings`
        //    la clave si es el sitio, y copiar aquel `foreach` habria puesto
        //    al ladron en la casilla numero 3.
        //
        // 2. Que la pieza exista no quiere decir que tenga sitio. Se exige
        //    `Position`, porque `UnaPieza` de una pieza sin posicion devuelve
        //    un objeto con `donde: null` que parece bueno y no lo es.
        //
        // Y se apunta DE DONDE salio, en `de`. No es adorno: si algun dia una
        // de las cuatro resulta ser la posicion inicial congelada en vez de la
        // de ahora, la unica forma de verlo es saber cual contesto.
        //
        // PERO ANTES QUE LAS CUATRO va la del propio juego. En el mismo
        // ensamblado esta:
        //
        //   static BoardQuery.GetRobberTile(CatanGameState) -> PositionedGamePiece
        //
        // que es exactamente la pregunta, contestada por quien la sabe. Es una
        // clase de `Catan.GameLogic.Queries` -- consultas, no operaciones: no
        // toca nada, y ademas esto corre en un postfix, con la accion ya
        // hecha. Preferirla a los campos no es un capricho: los campos hay que
        // acertarlos para cada tablero, y esto vale para el que sea, hoy y
        // cuando saquen otro. Los cuatro campos se quedan de respaldo por si
        // un dia le cambian el nombre al metodo.
        private static bool _ladronBuscado;
        private static bool _queryBuscada;
        private static MethodInfo _queryLadron;

        private static void BuscarLaQueryDelLadron()
        {
            if (_queryBuscada) return;
            _queryBuscada = true;
            try
            {
                foreach (Assembly a in AppDomain.CurrentDomain.GetAssemblies())
                {
                    if (a.GetName().Name != "Assembly-CSharp") continue;
                    Type t = a.GetType("Catan.GameLogic.Queries.BoardQuery");
                    if (t == null) break;
                    _queryLadron = t.GetMethod("GetRobberTile",
                        BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
                    break;
                }
            }
            catch (Exception) { }
            if (Plugin.Registro != null)
            {
                Plugin.Registro.LogInfo("el ladron: " +
                    (_queryLadron != null ? "se lee con BoardQuery.GetRobberTile"
                                          : "sin BoardQuery, se mirara el tablero a mano"));
            }
        }

        private static string Ladron(object catan, object tablero)
        {
            BuscarLaQueryDelLadron();
            if (_queryLadron != null && catan != null)
            {
                try
                {
                    string q = SitioDe(_queryLadron.Invoke(null, new object[] { catan }),
                                       "BoardQuery.GetRobberTile");
                    if (q != null) return q;
                }
                catch (Exception) { }   // si falla, quedan los cuatro campos
            }

            string s = SitioDe(Campo(tablero, "GamePiecesRobber"), "GamePiecesRobber");
            if (s != null) return s;
            s = SitioEnColeccion(Campo(tablero, "GamePiecesRobbers"), "GamePiecesRobbers");
            if (s != null) return s;
            s = SitioEnColeccion(Campo(tablero, "GamePiecesRobbersPerPlayerIdx"),
                                 "GamePiecesRobbersPerPlayerIdx");
            if (s != null) return s;

            // La red que no puede fallar: todas las piezas del tablero, y el
            // ladron es la que tiene `AsRobber`.
            IList todas = Campo(tablero, "GamePieces") as IList;
            if (todas != null)
            {
                for (int i = 0; i < todas.Count; i++)
                {
                    object pieza = Campo(todas[i], "Piece");
                    if (pieza == null || Campo(pieza, "AsRobber") == null) continue;
                    s = SitioDe(todas[i], "GamePieces");
                    if (s != null) return s;
                }
            }
            return "null";
        }

        // La pieza con su sitio, o null si no lo tiene. `null` de C#, no la
        // cadena "null": aqui hace falta distinguir «no esta» de «esta y dice
        // que no esta en ninguna parte».
        private static string SitioDe(object posicionada, string deDonde)
        {
            if (posicionada == null) return null;
            object donde = Campo(posicionada, "Position");
            if (donde == null) return null;
            string s = DescribirPieza(donde, posicionada);
            // El `de` se mete antes de cerrar la llave.
            return s.Substring(0, s.Length - 1)
                 + ",\"de\":\"" + Escapar(deDonde) + "\"}";
        }

        private static string SitioEnColeccion(object coleccion, string deDonde)
        {
            if (coleccion == null) return null;
            IDictionary d = coleccion as IDictionary;
            if (d != null)
            {
                // La clave es el indice del jugador, no el sitio: la posicion
                // sale de la pieza.
                foreach (DictionaryEntry e in d)
                {
                    string s = SitioDe(e.Value, deDonde);
                    if (s != null) return s;
                }
                return null;
            }
            IList l = coleccion as IList;
            if (l != null)
            {
                for (int i = 0; i < l.Count; i++)
                {
                    string s = SitioDe(l[i], deDonde);
                    if (s != null) return s;
                }
            }
            return null;
        }

        // Los NOMBRES de los campos y propiedades que llevan `trozo` dentro.
        // No lee ni un valor: es una lista de nombres. Se queda por si el
        // juego vuelve a mover al ladron de sitio en una version futura.
        private static string NombresQueSuenanA(object o, string trozo)
        {
            StringBuilder s = new StringBuilder("[");
            if (o != null)
            {
                bool primero = true;
                const BindingFlags COMO = BindingFlags.Public | BindingFlags.NonPublic
                                        | BindingFlags.Instance | BindingFlags.DeclaredOnly;
                Type t = o.GetType();
                while (t != null)
                {
                    FieldInfo[] campos = t.GetFields(COMO);
                    for (int i = 0; i < campos.Length; i++)
                    {
                        if (campos[i].Name.IndexOf(trozo, StringComparison.OrdinalIgnoreCase) < 0)
                            continue;
                        if (!primero) s.Append(",");
                        primero = false;
                        s.Append("\"").Append(Escapar(campos[i].Name)).Append("\"");
                    }
                    PropertyInfo[] props = t.GetProperties(COMO);
                    for (int i = 0; i < props.Length; i++)
                    {
                        if (props[i].Name.IndexOf(trozo, StringComparison.OrdinalIgnoreCase) < 0)
                            continue;
                        if (!primero) s.Append(",");
                        primero = false;
                        s.Append("\"").Append(Escapar(props[i].Name)).Append("\"");
                    }
                    t = t.BaseType;
                }
            }
            return s.Append("]").ToString();
        }

        private static string UnaPieza(object posicionada)
        {
            if (posicionada == null) return "null";
            return DescribirPieza(Campo(posicionada, "Position"), posicionada);
        }

        private static string DescribirPieza(object posicion, object posicionada)
        {
            object pieza = Campo(posicionada, "Piece");
            StringBuilder s = new StringBuilder("{");
            s.Append("\"donde\":").Append(Posicion(posicion));
            s.Append(",\"tipo\":\"").Append(Escapar(Texto(Campo(pieza, "Type")))).Append("\"");
            s.Append(",\"de_jugador\":").Append(Entero(pieza, "OwnedByPlayer"));
            // Solo si vienen. En el Catan basico son null siempre, asi que no
            // engordan nada; en Ciudades y Caballeros son lo que distingue un
            // caballero activo de uno dormido y de que nivel es, que sin esto
            // se perderia aunque la pieza si se apuntara.
            if (Campo(pieza, "IsActive") != null)
                s.Append(",\"activa\":").Append(Booleano(pieza, "IsActive"));
            if (Campo(pieza, "ActivateRoundNumber") != null)
                s.Append(",\"activada_en\":").Append(Entero(pieza, "ActivateRoundNumber"));
            if (Campo(pieza, "UpgradedRoundNumber") != null)
                s.Append(",\"mejorada_en\":").Append(Entero(pieza, "UpgradedRoundNumber"));
            s.Append("}");
            return s.ToString();
        }

        // Un HexGridPosition es una casilla, una arista o un vertice. Un
        // vertice lo forman las TRES casillas que lo tocan, y una arista las
        // DOS -- que es exactamente como el tracker nombra cada sitio.
        private static string Posicion(object hgp)
        {
            if (hgp == null) return "null";
            object cara = Campo(hgp, "AsFacePos");
            object arista = Campo(hgp, "AsEdgePos");
            object esquina = Campo(hgp, "AsCornerPos");
            string tipo = Texto(Campo(hgp, "PosType"));

            StringBuilder s = new StringBuilder("{\"que\":\"");
            s.Append(Escapar(tipo)).Append("\"");
            if (esquina != null && EsEsquina(tipo))
            {
                s.Append(",\"casillas\":[")
                 .Append(Cara(Campo(esquina, "FaceA"))).Append(",")
                 .Append(Cara(Campo(esquina, "FaceB"))).Append(",")
                 .Append(Cara(Campo(esquina, "FaceC"))).Append("]");
            }
            else if (arista != null && EsArista(tipo))
            {
                s.Append(",\"casillas\":[")
                 .Append(Cara(Campo(arista, "FaceA"))).Append(",")
                 .Append(Cara(Campo(arista, "FaceB"))).Append("]");
            }
            else if (cara != null)
            {
                s.Append(",\"casillas\":[").Append(Cara(cara)).Append("]");
            }
            return s.Append("}").ToString();
        }

        private static bool EsEsquina(string tipo)
        {
            return tipo != null && tipo.ToLowerInvariant().Contains("corner");
        }

        private static bool EsArista(string tipo)
        {
            return tipo != null && tipo.ToLowerInvariant().Contains("edge");
        }

        private static string Cara(object face)
        {
            if (face == null) return "null";
            return "[" + Entero(face, "X") + "," + Entero(face, "Y") + "]";
        }

        // De donde sale cada dato del jugador. Esto estuvo mal y hay que
        // decir por que, porque el error era invisible: se habia supuesto que
        // CatanPlayerState tenia PlayerId, Name, Color y VictoryPoints, y
        // leido el .dll con Mono.Cecil resulta que NO tiene ninguno de los
        // cuatro (solo Inventory, PlayerType, AiDifficulty y cosas asi). Los
        // cuatro habrian salido null en todas las partidas.
        //
        // Donde estan de verdad, verificado sobre el .dll:
        //
        //   id      CommonGameState.CommonPlayerStates[].Id      (Int32)
        //   hueco   CommonGameState.CommonPlayerStates[].SlotIdx (Int32)
        //   color   CommonGameState.ColorIdByPlayerId            (Dictionary)
        //   turno   CommonGameState.activePlayerId               (Int32)
        //
        // El NOMBRE del jugador no esta en la logica del juego: lo mas
        // parecido es CommunicationId, que es un identificador de red. Y los
        // puntos de victoria tampoco: no hay campo, se calculan. Ninguno de
        // los dos hace falta aqui -- lo que necesita el tracker para saber de
        // quien es una pieza es el id y el color, y esos si estan.
        // --- los puntos de victoria -------------------------------------
        // No hay ningun campo con los puntos: el juego los CALCULA. Estan en
        //   Catan.GameLogic.Rules.BaseVictoryPointsRule
        //     public static int GetTotalVictoryPoints(int, CatanGameState)
        //     public static int GetVisibleVictoryPoints(int, CatanGameState)
        //     public static int GetDevCardVictoryPoints(int, CatanGameState)
        // asi que se llaman por reflexion.
        //
        // SOLO SE LEEN LOS VISIBLES, y esto no es una preferencia: es la
        // linea que separa apuntar la partida de hacer trampas.
        //
        // Los VISIBLES son, por definicion, los que ven todos los que estan
        // en la mesa. Los TOTALES incluyen los puntos de las cartas de
        // desarrollo que el rival lleva ESCONDIDAS en la mano, y
        // GetDevCardVictoryPoints devuelve justo esos. Jugando contra la IA
        // daba igual y se apuntaban los tres. Jugando con personas, apuntar
        // los otros dos seria escribir en un fichero, en vivo, una carta que
        // nadie mas puede ver -- da igual que el fichero se lea despues: en
        // el momento en que se juega la partida el dato ya esta fuera.
        //
        // HAY UNA EXCEPCION, Y UNA SOLA: los puntos TOTALES se leen tambien,
        // pero unicamente en la accion de ganar la partida. Cuando alguien
        // gana, el juego enseña la pantalla de resultados con los puntos de
        // todos desglosados, cartas de punto de victoria incluidas. En ese
        // instante ya no son informacion oculta: los ven los cuatro.
        //
        // No es una comodidad, hace falta: sin ellos, los puntos finales que
        // se guardan de los que PIERDEN se quedan cortos -- les faltan las
        // cartas que llevaran tapadas -- y cualquier media de puntos por
        // partida sale sesgada a la baja para todos menos para el ganador.
        //
        // La guarda es por el NOMBRE de la accion y esta puesta en el unico
        // sitio desde donde se llama. GetDevCardVictoryPoints no se busca en
        // ningun caso: eso es "cuantos puntos escondidos lleva este" y no
        // hace falta para nada.
        private static MethodInfo _puntosTotales;
        //
        // El resto de lo que apunta el mod ya era publico y se ha repasado
        // campo a campo: 'cuentas' son las 12 estadisticas del juego
        // (poblados/ciudades/carreteras construidas, caballeros, comercios
        // aceptados y rechazados, cartas compradas, veces robado...), todas
        // cosas que pasan a la vista de todos. Los inventarios -- o sea las
        // manos -- no se leen en ningun sitio.
        private static bool _reglaBuscada;
        private static MethodInfo _puntosVisibles;

        private static void BuscarReglaDePuntos()
        {
            if (_reglaBuscada) return;
            _reglaBuscada = true;
            try
            {
                foreach (Assembly a in AppDomain.CurrentDomain.GetAssemblies())
                {
                    if (a.GetName().Name != "Assembly-CSharp") continue;
                    Type t = a.GetType("Catan.GameLogic.Rules.BaseVictoryPointsRule");
                    if (t == null) break;
                    BindingFlags f = BindingFlags.Public | BindingFlags.NonPublic |
                                     BindingFlags.Static;
                    _puntosVisibles = t.GetMethod("GetVisibleVictoryPoints", f);
                    _puntosTotales = t.GetMethod("GetTotalVictoryPoints", f);
                    break;
                }
            }
            catch (Exception) { }
            if (Plugin.Registro != null)
            {
                Plugin.Registro.LogInfo("puntos de victoria (solo los visibles): " +
                    (_puntosVisibles != null ? "se leen del juego"
                                             : "NO se ha encontrado el metodo"));
            }
        }

        private static string Puntos(MethodInfo m, object id, object catan)
        {
            if (m == null || id == null || catan == null) return "null";
            try
            {
                object v = m.Invoke(null, new object[] { id, catan });
                return v == null ? "null"
                                 : Convert.ToInt64(v).ToString(CultureInfo.InvariantCulture);
            }
            catch (Exception) { return "null"; }
        }

        // Las cuentas que el propio juego lleva de cada jugador: poblados y
        // ciudades construidos, comercios aceptados y rechazados, cartas de
        // desarrollo compradas, veces que le han robado... Se vuelcan todos
        // los campos simples que tenga, sin lista escrita a mano, para que
        // el dia que el juego anada uno aparezca solo.
        private static string Estadisticas(object catan, object id)
        {
            try
            {
                object estad = Campo(catan, "StatisticState");
                IDictionary porJugador = Campo(estad, "PlayerStatistics") as IDictionary;
                if (porJugador == null || id == null) return "null";
                foreach (DictionaryEntry e in porJugador)
                {
                    if (e.Key == null || e.Key.ToString() != id.ToString()) continue;
                    return NumerosDe(e.Value);
                }
            }
            catch (Exception) { }
            return "null";
        }

        private static string NumerosDe(object o)
        {
            if (o == null) return "null";
            StringBuilder s = new StringBuilder("{");
            bool primero = true;
            Type t = o.GetType();
            while (t != null && t != typeof(object))
            {
                FieldInfo[] fs = t.GetFields(BindingFlags.Public | BindingFlags.NonPublic |
                                             BindingFlags.Instance | BindingFlags.DeclaredOnly);
                for (int i = 0; i < fs.Length; i++)
                {
                    Type tf = fs[i].FieldType;
                    if (!(tf.IsPrimitive || tf.IsEnum)) continue;
                    if (fs[i].Name.IndexOf('<') >= 0) continue;
                    object v;
                    try { v = fs[i].GetValue(o); }
                    catch (Exception) { continue; }
                    if (v == null) continue;
                    if (!primero) s.Append(",");
                    primero = false;
                    s.Append("\"").Append(Escapar(fs[i].Name)).Append("\":");
                    if (tf == typeof(bool))
                        s.Append(((bool)v) ? "true" : "false");
                    else if (tf.IsEnum)
                        s.Append("\"").Append(Escapar(v.ToString())).Append("\"");
                    else
                    {
                        try { s.Append(Convert.ToInt64(v).ToString(CultureInfo.InvariantCulture)); }
                        catch (Exception) { s.Append("null"); }
                    }
                }
                t = t.BaseType;
            }
            return s.Append("}").ToString();
        }

        // `seAcabo` = esta es la accion de ganar la partida. Solo entonces se
        // escriben los puntos totales; ver el comentario de arriba.
        private static string Jugadores(object estadoComun, object catan, bool seAcabo)
        {
            BuscarReglaDePuntos();
            IDictionary colores = Campo(estadoComun, "ColorIdByPlayerId") as IDictionary;
            IEnumerable comunes = Campo(estadoComun, "CommonPlayerStates") as IEnumerable;
            IEnumerable propios = Campo(catan, "Player") as IEnumerable;

            // los de Catan van en el mismo orden que los comunes, asi que se
            // recorren en paralelo por posicion
            List<object> deCatan = new List<object>();
            if (propios != null) foreach (object p in propios) deCatan.Add(p);

            StringBuilder s = new StringBuilder("[");
            bool primero = true;
            int i = 0;
            if (comunes != null)
            {
                foreach (object p in comunes)
                {
                    if (p == null) { i++; continue; }
                    if (!primero) s.Append(",");
                    primero = false;
                    // El color NO se busca por el numero de jugador aunque el
                    // campo se llame ColorIdByPlayerId: medido en la primera
                    // partida grabada, la clave es el identificador de red.
                    //     {'e6397905-4850-...': 'Orange',
                    //      'Jean_hard': 'CremeWhite', 'Louis_hard': 'Purple'}
                    // Buscando por el numero (0-3) no casaba ninguno y el
                    // color salia vacio en los cuatro jugadores.
                    object clave = Campo(p, "CommunicationId");
                    object id = Campo(p, "Id");
                    s.Append("{\"id\":").Append(Entero(p, "Id"));
                    s.Append(",\"hueco\":").Append(Entero(p, "SlotIdx"));
                    s.Append(",\"color\":\"").Append(ColorDe(colores, clave)).Append("\"");
                    s.Append(",\"red\":\"").Append(Escapar(Texto(Campo(p, "CommunicationId")))).Append("\"");
                    object suyo = i < deCatan.Count ? deCatan[i] : null;
                    s.Append(",\"tipo\":\"").Append(Escapar(Texto(Campo(suyo, "PlayerType")))).Append("\"");
                    s.Append(",\"puntos_visibles\":").Append(Puntos(_puntosVisibles, id, catan));
                    if (seAcabo)
                        s.Append(",\"puntos_finales\":").Append(Puntos(_puntosTotales, id, catan));
                    s.Append(",\"cuentas\":").Append(Estadisticas(catan, id));
                    s.Append("}");
                    i++;
                }
            }
            return s.Append("]").ToString();
        }

        private static string ColorDe(IDictionary colores, object clave)
        {
            if (colores == null || clave == null) return "";
            try
            {
                foreach (DictionaryEntry e in colores)
                {
                    if (e.Key != null && e.Key.ToString() == clave.ToString())
                        return e.Value == null ? "" : Escapar(e.Value.ToString());
                }
            }
            catch (Exception) { }
            return "";
        }

        private static string Diccionario(object d)
        {
            IDictionary m = d as IDictionary;
            if (m == null) return "null";
            StringBuilder s = new StringBuilder("{");
            bool primero = true;
            foreach (DictionaryEntry e in m)
            {
                if (!primero) s.Append(",");
                primero = false;
                s.Append("\"").Append(Escapar(Texto(e.Key))).Append("\":\"")
                 .Append(Escapar(Texto(e.Value))).Append("\"");
            }
            return s.Append("}").ToString();
        }

        // --- el esquema real del juego ---------------------------------
        // Se escribe una linea al principio del fichero con los miembros que
        // tienen de verdad las clases que se leen, y el valor de los que son
        // simples. Sirve para dos cosas: comprobar que lo que se esta leyendo
        // es lo que se cree, y arreglar de una vez cualquier nombre que no
        // sea el correcto sin tener que jugar otra partida para averiguarlo.
        private static void VolcarEsquema(object estadoComun, object catan,
                                          object tablero, object partida)
        {
            try
            {
                object comunes = Campo(estadoComun, "CommonPlayerStates");
                object propios = Campo(catan, "Player");
                StringBuilder j = new StringBuilder(8192);
                j.Append("{\"n\":0,\"esquema\":{");
                j.Append("\"estado\":").Append(Miembros(estadoComun));
                j.Append(",\"catan\":").Append(Miembros(catan));
                j.Append(",\"tablero\":").Append(Miembros(tablero));
                j.Append(",\"partida\":").Append(Miembros(partida));
                j.Append(",\"jugador_comun\":").Append(Miembros(Primero(comunes)));
                j.Append(",\"jugador_catan\":").Append(Miembros(Primero(propios)));
                j.Append(",\"colores\":").Append(
                    Diccionario(Campo(estadoComun, "ColorIdByPlayerId")));
                j.Append(",\"num_jugadores\":").Append(Cuantos(comunes));
                j.Append("}}");
                lock (Plugin.Candado)
                {
                    if (Plugin.Salida != null) Plugin.Salida.WriteLine(j.ToString());
                }
                if (Plugin.Registro != null)
                    Plugin.Registro.LogInfo("esquema volcado; jugadores encontrados: " +
                                            Cuantos(comunes));
            }
            catch (Exception e)
            {
                if (Plugin.Registro != null)
                    Plugin.Registro.LogWarning("no se pudo volcar el esquema: " + e.Message);
            }
        }

        private static object Primero(object lista)
        {
            IEnumerable e = lista as IEnumerable;
            if (e == null) return null;
            foreach (object o in e) { if (o != null) return o; }
            return null;
        }

        private static string Cuantos(object lista)
        {
            IEnumerable e = lista as IEnumerable;
            if (e == null) return "null";
            int n = 0;
            foreach (object o in e) n++;
            return n.ToString(CultureInfo.InvariantCulture);
        }

        private static string Miembros(object o)
        {
            if (o == null) return "null";
            StringBuilder s = new StringBuilder("{\"tipo\":\"");
            s.Append(Escapar(o.GetType().FullName)).Append("\",\"campos\":{");
            bool primero = true;
            Type t = o.GetType();
            while (t != null && t != typeof(object))
            {
                MemberInfo[] ms = t.GetMembers(BindingFlags.Public | BindingFlags.NonPublic |
                                               BindingFlags.Instance | BindingFlags.DeclaredOnly);
                for (int i = 0; i < ms.Length; i++)
                {
                    string nombre = ms[i].Name;
                    Type tipo = null;
                    if (ms[i] is FieldInfo) tipo = ((FieldInfo)ms[i]).FieldType;
                    else if (ms[i] is PropertyInfo)
                    {
                        PropertyInfo p = (PropertyInfo)ms[i];
                        if (!p.CanRead || p.GetIndexParameters().Length > 0) continue;
                        tipo = p.PropertyType;
                    }
                    else continue;
                    if (nombre.IndexOf('<') >= 0) continue;  // campos de respaldo generados
                    if (!primero) s.Append(",");
                    primero = false;
                    s.Append("\"").Append(Escapar(nombre)).Append("\":\"")
                     .Append(Escapar(tipo.Name));
                    // el valor solo si es simple: llamar a un getter cualquiera
                    // dentro de una accion del juego puede costar caro o fallar
                    string valor = ValorSimple(o, nombre, tipo);
                    if (valor != null) s.Append(" = ").Append(Escapar(valor));
                    s.Append("\"");
                }
                t = t.BaseType;
            }
            return s.Append("}}").ToString();
        }

        private static string ValorSimple(object o, string nombre, Type tipo)
        {
            if (!(tipo == typeof(string) || tipo.IsPrimitive || tipo.IsEnum)) return null;
            try
            {
                object v = Campo(o, nombre);
                if (v == null) return "null";
                string s = v.ToString();
                return s.Length > 60 ? s.Substring(0, 60) : s;
            }
            catch { return null; }
        }

        // --- utilidades de reflexion -----------------------------------
        // Un objeto entero a JSON, sin saber que campos tiene.
        //
        // NO ES DE USO GENERAL, y por eso no esta arriba con los demas
        // ayudantes: solo se usa con objetos pedidos por su nombre y de los
        // que se sabe que llevan informacion publica. Pasarle el estado de
        // accion entero volcaria tambien las cartas de la mano de la gente.
        //
        // `hondo` corta la recursion: estos modelos tienen referencias
        // cruzadas y sin limite se recorre medio juego por cada accion.
        private static string Volcado(object o, int hondo)
        {
            if (o == null) return "null";
            Type t = o.GetType();
            if (o is string) return "\"" + Escapar((string)o) + "\"";
            if (t.IsEnum) return "\"" + Escapar(o.ToString()) + "\"";
            if (o is bool) return ((bool)o) ? "true" : "false";
            if (t.IsPrimitive)
            {
                try { return Convert.ToString(o, CultureInfo.InvariantCulture); }
                catch (Exception) { return "null"; }
            }
            if (hondo <= 0) return "\"...\"";

            IDictionary dic = o as IDictionary;
            if (dic != null)
            {
                StringBuilder sd = new StringBuilder("{");
                bool p1 = true;
                foreach (DictionaryEntry e in dic)
                {
                    if (!p1) sd.Append(",");
                    p1 = false;
                    sd.Append("\"").Append(Escapar(Texto(e.Key))).Append("\":")
                      .Append(Volcado(e.Value, hondo - 1));
                }
                return sd.Append("}").ToString();
            }

            IEnumerable lista = o as IEnumerable;
            if (lista != null)
            {
                StringBuilder sl = new StringBuilder("[");
                bool p2 = true;
                foreach (object v in lista)
                {
                    if (!p2) sl.Append(",");
                    p2 = false;
                    sl.Append(Volcado(v, hondo - 1));
                }
                return sl.Append("]").ToString();
            }

            StringBuilder s = new StringBuilder("{");
            bool primero = true;
            foreach (FieldInfo f in t.GetFields(BindingFlags.Public |
                                                BindingFlags.Instance))
            {
                object v;
                try { v = f.GetValue(o); }
                catch (Exception) { continue; }
                if (v == null) continue;
                if (!primero) s.Append(",");
                primero = false;
                s.Append("\"").Append(Escapar(f.Name)).Append("\":")
                 .Append(Volcado(v, hondo - 1));
            }
            foreach (PropertyInfo p in t.GetProperties(BindingFlags.Public |
                                                       BindingFlags.Instance))
            {
                if (!p.CanRead || p.GetIndexParameters().Length > 0) continue;
                object v;
                try { v = p.GetValue(o, null); }
                catch (Exception) { continue; }
                if (v == null) continue;
                if (!primero) s.Append(",");
                primero = false;
                s.Append("\"").Append(Escapar(p.Name)).Append("\":")
                 .Append(Volcado(v, hondo - 1));
            }
            return s.Append("}").ToString();
        }

        private static object Campo(object o, string nombre)
        {
            if (o == null) return null;
            Type t = o.GetType();
            while (t != null)
            {
                FieldInfo f = t.GetField(nombre, BindingFlags.Public | BindingFlags.NonPublic |
                                                 BindingFlags.Instance | BindingFlags.DeclaredOnly);
                if (f != null) return f.GetValue(o);
                PropertyInfo p = t.GetProperty(nombre, BindingFlags.Public | BindingFlags.NonPublic |
                                                       BindingFlags.Instance | BindingFlags.DeclaredOnly);
                if (p != null && p.CanRead) return p.GetValue(o, null);
                t = t.BaseType;
            }
            return null;
        }

        private static string Entero(object o, string nombre)
        {
            object v = Campo(o, nombre);
            if (v == null) return "null";
            try { return Convert.ToInt64(v).ToString(CultureInfo.InvariantCulture); }
            catch { return "null"; }
        }

        private static string ListaDeEnteros(object lista)
        {
            IEnumerable e = lista as IEnumerable;
            if (e == null) return "[]";
            StringBuilder s = new StringBuilder("[");
            bool primero = true;
            foreach (object v in e)
            {
                if (!primero) s.Append(",");
                primero = false;
                try { s.Append(Convert.ToInt64(v).ToString(CultureInfo.InvariantCulture)); }
                catch { s.Append("null"); }
            }
            return s.Append("]").ToString();
        }

        private static string Texto(object o)
        {
            return o == null ? "" : o.ToString();
        }

        private static void Par(StringBuilder j, string clave, string valorCrudo, bool coma)
        {
            if (coma) j.Append(",");
            j.Append("\"").Append(clave).Append("\":").Append(valorCrudo);
        }

        private static string Escapar(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            StringBuilder r = new StringBuilder(s.Length + 8);
            foreach (char c in s)
            {
                if (c == '"' || c == '\\') r.Append('\\').Append(c);
                else if (c == '\n') r.Append("\\n");
                else if (c == '\r') r.Append("\\r");
                else if (c == '\t') r.Append("\\t");
                else if (c < ' ') r.Append("\\u").Append(((int)c).ToString("x4"));
                else r.Append(c);
            }
            return r.ToString();
        }
    }
}
