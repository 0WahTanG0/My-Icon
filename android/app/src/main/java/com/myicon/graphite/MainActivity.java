package com.myicon.graphite;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.content.res.Resources;
import android.content.res.XmlResourceParser;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Build;
import android.os.Bundle;
import android.util.DisplayMetrics;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.TextView;
import android.widget.Toast;

import org.xmlpull.v1.XmlPullParser;

import java.text.Collator;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * Icon pack home screen: stats, "copy my apps" for the next pack version,
 * how-to-apply, and a grid of all icons (also used as icon picker).
 */
public class MainActivity extends Activity {

    private static final String THEME_PARK = "com.samsung.android.themedesigner";
    private static final String NOVA = "com.teslacoilsw.launcher";

    /** One launcher activity of the phone. */
    private static final class App {
        final String label;
        final String component;   // package/activity
        final boolean themed;

        App(String label, String component, boolean themed) {
            this.label = label;
            this.component = component;
            this.themed = themed;
        }
    }

    private final List<Integer> iconIds = new ArrayList<>();
    private final List<String> iconNames = new ArrayList<>();
    private volatile List<App> apps;
    private boolean pickMode;
    private TextView stats;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        String action = getIntent() != null ? getIntent().getAction() : null;
        pickMode = action != null && action.endsWith("PICK_ICON");

        loadIcons();

        ListView list = findViewById(R.id.list);
        View header = getLayoutInflater().inflate(R.layout.header, list, false);
        list.addHeaderView(header, null, false);
        stats = header.findViewById(R.id.stats);

        if (pickMode) {
            header.findViewById(R.id.tools).setVisibility(View.GONE);
            header.findViewById(R.id.style_card).setVisibility(View.GONE);
            header.findViewById(R.id.apply_card).setVisibility(View.GONE);
            ((TextView) header.findViewById(R.id.icons_header)).setText(R.string.pick_title);
        } else {
            setupTools(header);
            new StylesCard(this, header).load();
        }

        DisplayMetrics dm = getResources().getDisplayMetrics();
        float widthDp = dm.widthPixels / dm.density;
        int cols = Math.max(4, (int) ((widthDp - 16) / 82));
        list.setAdapter(new IconRows(cols, (int) (dm.widthPixels - 16 * dm.density)));

        if (!pickMode) {
            new Thread(this::scanApps, "scan-apps").start();
        }
    }

    // ------------------------------------------------------------------ icons

    private void loadIcons() {
        Resources res = getResources();
        String[] names = res.getStringArray(R.array.icon_pack);
        String[] labels = res.getStringArray(R.array.icon_names);
        for (int i = 0; i < names.length; i++) {
            int id = res.getIdentifier(names[i], "drawable", getPackageName());
            if (id != 0) {
                iconIds.add(id);
                iconNames.add(i < labels.length ? labels[i] : names[i]);
            }
        }
    }

    private void onIconClick(int index) {
        int id = iconIds.get(index);
        if (!pickMode) {
            Toast.makeText(this, iconNames.get(index), Toast.LENGTH_SHORT).show();
            return;
        }
        Intent result = new Intent();
        try {
            Bitmap bmp = BitmapFactory.decodeResource(getResources(), id);
            result.putExtra("icon", bmp);
        } catch (OutOfMemoryError ignored) {
        }
        result.putExtra(Intent.EXTRA_SHORTCUT_ICON_RESOURCE,
                Intent.ShortcutIconResource.fromContext(this, id));
        setResult(RESULT_OK, result);
        finish();
    }

    private final class IconRows extends BaseAdapter {
        private final int cols;
        private final int cell;

        IconRows(int cols, int widthPx) {
            this.cols = cols;
            this.cell = widthPx / cols;
        }

        @Override
        public int getCount() {
            return (iconIds.size() + cols - 1) / cols;
        }

        @Override
        public Object getItem(int position) {
            return position;
        }

        @Override
        public long getItemId(int position) {
            return position;
        }

        @Override
        public View getView(int position, View convertView, ViewGroup parent) {
            LinearLayout row = (LinearLayout) convertView;
            if (row == null) {
                row = new LinearLayout(MainActivity.this);
                row.setOrientation(LinearLayout.HORIZONTAL);
                row.setGravity(Gravity.CENTER_HORIZONTAL);
                int pad = (int) (8 * getResources().getDisplayMetrics().density);
                for (int c = 0; c < cols; c++) {
                    ImageView iv = new ImageView(MainActivity.this);
                    iv.setPadding(pad / 2, pad / 2, pad / 2, pad / 2);
                    iv.setScaleType(ImageView.ScaleType.FIT_CENTER);
                    row.addView(iv, new LinearLayout.LayoutParams(cell, cell));
                }
            }
            for (int c = 0; c < cols; c++) {
                final int index = position * cols + c;
                ImageView iv = (ImageView) row.getChildAt(c);
                if (index < iconIds.size()) {
                    iv.setImageResource(iconIds.get(index));
                    iv.setContentDescription(iconNames.get(index));
                    iv.setOnClickListener(v -> onIconClick(index));
                    iv.setVisibility(View.VISIBLE);
                } else {
                    iv.setImageDrawable(null);
                    iv.setOnClickListener(null);
                    iv.setVisibility(View.INVISIBLE);
                }
            }
            return row;
        }
    }

    // ------------------------------------------------------------------ tools

    private void setupTools(View header) {
        Button copy = header.findViewById(R.id.copy);
        Button share = header.findViewById(R.id.share);
        CheckBox all = header.findViewById(R.id.include_all);

        copy.setOnClickListener(v -> {
            String text = buildReport(all.isChecked());
            if (text == null) return;
            ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            cm.setPrimaryClip(ClipData.newPlainText("My-Icon apps", text));
            int n = countLines(all.isChecked());
            Toast.makeText(this, getString(R.string.copied, n), Toast.LENGTH_LONG).show();
        });
        share.setOnClickListener(v -> {
            String text = buildReport(all.isChecked());
            if (text == null) return;
            Intent send = new Intent(Intent.ACTION_SEND);
            send.setType("text/plain");
            send.putExtra(Intent.EXTRA_SUBJECT, getString(R.string.share_title));
            send.putExtra(Intent.EXTRA_TEXT, text);
            startActivity(Intent.createChooser(send, getString(R.string.share_title)));
        });

        PackageManager pm = getPackageManager();
        Button themePark = header.findViewById(R.id.theme_park);
        Intent tp = pm.getLaunchIntentForPackage(THEME_PARK);
        if (tp != null) {
            themePark.setVisibility(View.VISIBLE);
            themePark.setOnClickListener(v -> safeStart(tp));
        }
        Button nova = header.findViewById(R.id.nova);
        if (isInstalled(NOVA)) {
            nova.setVisibility(View.VISIBLE);
            nova.setOnClickListener(v -> {
                Intent apply = new Intent("com.teslacoilsw.launcher.APPLY_ICON_THEME");
                apply.setPackage(NOVA);
                apply.putExtra("com.teslacoilsw.launcher.extra.ICON_THEME_TYPE", "GO");
                apply.putExtra("com.teslacoilsw.launcher.extra.ICON_THEME_PACKAGE", getPackageName());
                apply.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                safeStart(apply);
            });
        }
    }

    private boolean isInstalled(String pkg) {
        try {
            getPackageManager().getPackageInfo(pkg, 0);
            return true;
        } catch (PackageManager.NameNotFoundException e) {
            return false;
        }
    }

    private void safeStart(Intent intent) {
        try {
            startActivity(intent);
        } catch (Exception e) {
            Toast.makeText(this, R.string.not_found, Toast.LENGTH_SHORT).show();
        }
    }

    /** All "package/activity" components listed in appfilter.xml. */
    private Set<String> themedComponents() {
        Set<String> set = new HashSet<>();
        try (XmlResourceParser p = getResources().getXml(R.xml.appfilter)) {
            int ev;
            while ((ev = p.next()) != XmlPullParser.END_DOCUMENT) {
                if (ev != XmlPullParser.START_TAG) continue;
                String tag = p.getName();
                if (!"item".equals(tag) && !"calendar".equals(tag)) continue;
                String comp = p.getAttributeValue(null, "component");
                if (comp == null) continue;
                if (comp.startsWith("ComponentInfo{") && comp.endsWith("}")) {
                    comp = comp.substring(14, comp.length() - 1);
                }
                ComponentName cn = ComponentName.unflattenFromString(comp);
                if (cn != null) set.add(cn.getPackageName() + "/" + cn.getClassName());
            }
        } catch (Exception e) {
            // a broken appfilter would show up as "everything missing"
        }
        return set;
    }

    private void scanApps() {
        Set<String> themed = themedComponents();
        PackageManager pm = getPackageManager();
        Intent main = new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> infos = pm.queryIntentActivities(main, 0);
        List<App> result = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        for (ResolveInfo ri : infos) {
            String pkg = ri.activityInfo.packageName;
            if (pkg.equals(getPackageName())) continue;
            String comp = pkg + "/" + ri.activityInfo.name;
            if (!seen.add(comp)) continue;
            CharSequence label = ri.loadLabel(pm);
            result.add(new App(label != null ? label.toString().trim() : pkg, comp, themed.contains(comp)));
        }
        Collator col = Collator.getInstance(new Locale("ru"));
        Collections.sort(result, (a, b) -> col.compare(a.label, b.label));
        apps = result;
        int have = 0;
        for (App a : result) if (a.themed) have++;
        final int haveF = have;
        runOnUiThread(() -> stats.setText(getString(R.string.stats, iconIds.size(), haveF, result.size())));
    }

    private int countLines(boolean includeAll) {
        int n = 0;
        if (apps != null) for (App a : apps) if (includeAll || !a.themed) n++;
        return n;
    }

    private String buildReport(boolean includeAll) {
        List<App> list = apps;
        if (list == null) {
            Toast.makeText(this, R.string.stats_loading, Toast.LENGTH_SHORT).show();
            return null;
        }
        int missing = 0;
        for (App a : list) if (!a.themed) missing++;
        String version;
        try {
            version = getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
        } catch (PackageManager.NameNotFoundException e) {
            version = "?";
        }
        StringBuilder sb = new StringBuilder();
        sb.append(getString(R.string.app_name)).append(' ').append(version).append(" — без иконки: ").append(missing)
                .append(" из ").append(list.size()).append('\n');
        sb.append(Build.MANUFACTURER).append(' ').append(Build.MODEL)
                .append(", Android ").append(Build.VERSION.RELEASE).append('\n');
        sb.append("Формат: название | пакет/activity").append(includeAll ? " | есть/нет" : "").append("\n\n");
        for (App a : list) {
            if (!includeAll && a.themed) continue;
            sb.append(a.label.replace('|', '/')).append(" | ").append(a.component);
            if (includeAll) sb.append(a.themed ? " | есть" : " | нет");
            sb.append('\n');
        }
        return sb.toString();
    }
}
