package com.myicon.graphite;

import android.app.Activity;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.util.TypedValue;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;

/**
 * "Icon style" card: reads styles.json from the latest release, offers an update
 * of the current style, and lets the user switch to any other style (each style
 * is a build of this same app, installed over it).
 */
final class StylesCard {

    private final Activity a;
    private final TextView status;
    private final Button update;
    private final LinearLayout list;
    private volatile boolean busy;

    StylesCard(Activity activity, View header) {
        a = activity;
        status = header.findViewById(R.id.style_status);
        update = header.findViewById(R.id.update_button);
        list = header.findViewById(R.id.styles_list);
        TextView current = header.findViewById(R.id.style_current);
        current.setText(a.getString(R.string.style_current, a.getString(R.string.style_name), versionName()));
    }

    private String versionName() {
        try {
            return a.getPackageManager().getPackageInfo(a.getPackageName(), 0).versionName;
        } catch (PackageManager.NameNotFoundException e) {
            return "?";
        }
    }

    void load() {
        new Thread(() -> {
            try {
                JSONObject doc = new JSONObject(Installer.getText(Installer.RELEASE + "styles.json"));
                a.runOnUiThread(() -> show(doc));
            } catch (Exception e) {
                a.runOnUiThread(() -> status.setText(R.string.styles_offline));
            }
        }, "styles").start();
    }

    private int dp(int v) {
        return (int) TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v, a.getResources().getDisplayMetrics());
    }

    private void show(JSONObject doc) {
        status.setText(R.string.styles_hint);
        int code = doc.optInt("code", 0);
        String version = doc.optString("version", "");
        JSONArray styles = doc.optJSONArray("styles");
        if (styles == null) return;

        if (code > BuildConfig.VERSION_CODE) {
            String apk = null;
            for (int i = 0; i < styles.length(); i++) {
                JSONObject s = styles.optJSONObject(i);
                if (s != null && BuildConfig.STYLE_ID.equals(s.optString("id"))) apk = s.optString("apk");
            }
            if (apk != null) {
                final String file = apk;
                update.setVisibility(View.VISIBLE);
                update.setText(a.getString(R.string.update_available, version));
                update.setOnClickListener(v -> install(file));
            }
        }

        list.removeAllViews();
        for (int i = 0; i < styles.length(); i++) {
            JSONObject s = styles.optJSONObject(i);
            if (s == null) continue;
            String id = s.optString("id");
            boolean active = BuildConfig.STYLE_ID.equals(id) && code <= BuildConfig.VERSION_CODE;
            boolean mine = BuildConfig.STYLE_ID.equals(id);

            LinearLayout card = new LinearLayout(a);
            card.setOrientation(LinearLayout.VERTICAL);
            card.setPadding(0, dp(14), 0, 0);

            ImageView preview = new ImageView(a);
            preview.setAdjustViewBounds(true);
            preview.setScaleType(ImageView.ScaleType.FIT_CENTER);
            preview.setMinimumHeight(dp(40));
            card.addView(preview, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT));
            loadPreview(preview, s.optString("preview"));

            LinearLayout row = new LinearLayout(a);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setPadding(0, dp(6), 0, 0);
            TextView name = new TextView(a);
            name.setText(s.optString("name") + "\n" + s.optString("about"));
            name.setTextColor(a.getResources().getColor(R.color.text));
            name.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
            row.addView(name, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1));

            Button b = new Button(a);
            b.setAllCaps(false);
            b.setTextColor(a.getResources().getColor(R.color.text));
            b.setBackgroundResource(R.drawable.button_bg);
            b.setMinHeight(dp(44));
            b.setPadding(dp(16), 0, dp(16), 0);
            if (mine && active) {
                b.setText(R.string.style_active);
                b.setEnabled(false);
                b.setAlpha(0.6f);
            } else {
                b.setText(mine ? a.getString(R.string.update_available, version) : a.getString(R.string.style_install));
                final String apk = s.optString("apk");
                b.setOnClickListener(v -> install(apk));
            }
            row.addView(b, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT));
            card.addView(row);
            list.addView(card);
        }
    }

    private void loadPreview(ImageView view, String file) {
        if (file == null || file.isEmpty()) return;
        new Thread(() -> {
            try {
                Bitmap bmp = Installer.getBitmap(Installer.RELEASE + file);
                if (bmp != null) a.runOnUiThread(() -> view.setImageBitmap(bmp));
            } catch (Exception ignored) {
                // no preview: the name is still shown
            }
        }, "preview").start();
    }

    private void install(String apk) {
        if (busy) return;
        if (Installer.needsPermission(a)) {
            Toast.makeText(a, R.string.allow_install, Toast.LENGTH_LONG).show();
            Installer.askPermission(a);
            return;
        }
        busy = true;
        status.setText(a.getString(R.string.downloading, 0));
        new Thread(() -> {
            try {
                File f = Installer.download(a, Installer.RELEASE + apk,
                        p -> a.runOnUiThread(() -> status.setText(a.getString(R.string.downloading, p))));
                a.runOnUiThread(() -> status.setText(R.string.installing));
                Installer.install(a, f);
            } catch (Exception e) {
                a.runOnUiThread(() -> status.setText(a.getString(R.string.download_failed, e.getMessage())));
            } finally {
                busy = false;
            }
        }, "install").start();
    }
}
