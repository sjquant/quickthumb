import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.drawable.Drawable;
import android.os.Build;
import java.io.OutputStream;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Assert;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.GraphicsMode;
import org.robolectric.shadow.api.Shadow;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 35, manifest = Config.NONE, qualifiers = "mdpi")
@GraphicsMode(GraphicsMode.Mode.NATIVE)
public class NativeLottieTest {
  @Test public void renderActualAndroidLibrary() throws Exception {
    Path output = Path.of(System.getProperty("output"));
    Files.createDirectories(output);
    JSONArray cases = new JSONObject(Files.readString(Path.of(System.getProperty("cases"))))
        .getJSONArray("cases");
    Class<?> factory = Class.forName("com.airbnb.lottie.LottieCompositionFactory");
    Class<?> drawableType = Class.forName("com.airbnb.lottie.LottieDrawable");
    Class<?> compositionType = Class.forName("com.airbnb.lottie.LottieComposition");
    Class<?> modeType = Class.forName("com.airbnb.lottie.RenderMode");
    JSONArray observations = new JSONArray();
    int errors = 0;
    for (int i = 0; i < cases.length(); i++) {
      JSONObject item = cases.getJSONObject(i);
      JSONObject row = new JSONObject().put("name", item.getString("name"));
      try {
        String raw = Files.readString(Path.of(item.getString("payload")));
        String control = item.optString("control", "");
        if (control.equals("blank")) {
          raw = new JSONObject(raw).put("layers", new JSONArray()).toString();
        }
        // Preserve the original bytes for all positive cases: no input normalization.
        Object result = factory.getMethod("fromJsonStringSync", String.class, String.class)
            .invoke(null, raw, null);
        Object composition = result.getClass().getMethod("getValue").invoke(result);
        if (composition == null) {
          throw new AssertionError("Lottie parse failed: "
              + result.getClass().getMethod("getException").invoke(result));
        }
        Object instance = drawableType.getConstructor().newInstance();
        drawableType.getMethod("setComposition", compositionType).invoke(instance, composition);
        drawableType.getMethod("setRenderMode", modeType)
            .invoke(instance, modeType.getField("SOFTWARE").get(null));
        double frame = control.equals("frozen") ? 0 : item.getDouble("frame");
        if (frame != Math.rint(frame)) throw new IllegalArgumentException("Whole frames required");
        drawableType.getMethod("setFrame", int.class).invoke(instance, (int) frame);
        Drawable drawable = (Drawable) instance;
        int width = item.getInt("width"), height = item.getInt("height");
        drawable.setBounds(0, 0, width, height);
        Bitmap bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bitmap);
        drawable.draw(canvas);
        Path png = output.resolve(item.getString("name") + "-android.png");
        try (OutputStream stream = Files.newOutputStream(png)) {
          Assert.assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream));
        }
        row.put("screenshot", png.toString());
        row.put("frame", drawableType.getMethod("getFrame").invoke(instance));
        row.put("warnings", compositionType.getMethod("getWarnings").invoke(composition).toString());
        row.put("bitmap_shadow", Shadow.extract(bitmap).getClass().getName());
        row.put("canvas_shadow", Shadow.extract(canvas).getClass().getName());
      } catch (Throwable error) {
        Throwable cause = error instanceof InvocationTargetException ? error.getCause() : error;
        row.put("error", cause.toString());
        errors++;
      }
      observations.put(row);
    }
    Method loaded = Class.forName("org.robolectric.nativeruntime.DefaultNativeRuntimeLoader")
        .getDeclaredMethod("isLoaded");
    loaded.setAccessible(true);
    boolean nativeLoaded = (boolean) loaded.invoke(null);
    JSONObject report = new JSONObject().put("api", RuntimeEnvironment.getApiLevel())
        .put("android_release", Build.VERSION.RELEASE).put("graphics_mode", "NATIVE")
        .put("native_runtime_loaded", nativeLoaded).put("lottie_android", "6.7.1")
        .put("robolectric", "4.17").put("java_version", System.getProperty("java.version"))
        .put("os", System.getProperty("os.name")).put("arch", System.getProperty("os.arch"))
        .put("cases", observations);
    Files.writeString(output.resolve("execution.json"), report.toString(2));
    Assert.assertTrue("Native graphics runtime must actually load", nativeLoaded);
    Assert.assertEquals("Render exceptions; inspect execution.json", 0, errors);
  }
}
