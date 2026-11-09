package com.myicon.graphite;

import android.app.Activity;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInstaller;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Downloads files from the latest GitHub release and installs an APK of this
 * app (another style, or an update) through PackageInstaller.
 */
final class Installer {

    static final String RELEASE = "https://github.com/0WahTanG0/My-Icon/releases/latest/download/";

    interface Progress {
        void onProgress(int percent);
    }

    private Installer() {
    }

    private static HttpURLConnection open(String url) throws IOException {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setInstanceFollowRedirects(true);   // github.com -> objects.githubusercontent.com
        c.setConnectTimeout(15000);
        c.setReadTimeout(30000);
        c.setRequestProperty("User-Agent", "My-Icon-App");
        int code = c.getResponseCode();
        if (code != 200) {
            c.disconnect();
            throw new IOException("HTTP " + code);
        }
        return c;
    }

    static String getText(String url) throws IOException {
        HttpURLConnection c = open(url);
        try (InputStream in = c.getInputStream()) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            return out.toString("UTF-8");
        } finally {
            c.disconnect();
        }
    }

    static Bitmap getBitmap(String url) throws IOException {
        HttpURLConnection c = open(url);
        try (InputStream in = c.getInputStream()) {
            return BitmapFactory.decodeStream(in);
        } finally {
            c.disconnect();
        }
    }

    static File download(Context ctx, String url, Progress progress) throws IOException {
        File f = new File(ctx.getCacheDir(), "style.apk");
        HttpURLConnection c = open(url);
        long total = c.getContentLength();
        try (InputStream in = c.getInputStream(); OutputStream out = new FileOutputStream(f)) {
            byte[] buf = new byte[64 * 1024];
            long done = 0;
            int n, last = -1;
            while ((n = in.read(buf)) > 0) {
                out.write(buf, 0, n);
                done += n;
                if (total > 0) {
                    int p = (int) (done * 100 / total);
                    if (p != last) {
                        last = p;
                        progress.onProgress(p);
                    }
                }
            }
        } finally {
            c.disconnect();
        }
        return f;
    }

    /** True when the user still has to allow installs from this app (Android 8+). */
    static boolean needsPermission(Activity a) {
        return Build.VERSION.SDK_INT >= 26 && !a.getPackageManager().canRequestPackageInstalls();
    }

    static void askPermission(Activity a) {
        if (Build.VERSION.SDK_INT >= 26) {
            Intent i = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                    Uri.parse("package:" + a.getPackageName()));
            a.startActivity(i);
        }
    }

    /** Hands the APK to the system installer; the result arrives in InstallReceiver. */
    static void install(Context ctx, File apk) throws IOException {
        PackageInstaller pi = ctx.getPackageManager().getPackageInstaller();
        PackageInstaller.SessionParams params =
                new PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL);
        int id = pi.createSession(params);
        try (PackageInstaller.Session s = pi.openSession(id)) {
            try (InputStream in = new FileInputStream(apk);
                 OutputStream out = s.openWrite("style.apk", 0, apk.length())) {
                byte[] buf = new byte[64 * 1024];
                int n;
                while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
                s.fsync(out);
            }
            Intent cb = new Intent(ctx, InstallReceiver.class);
            int flags = PendingIntent.FLAG_UPDATE_CURRENT;
            if (Build.VERSION.SDK_INT >= 31) flags |= PendingIntent.FLAG_MUTABLE;
            PendingIntent pending = PendingIntent.getBroadcast(ctx, id, cb, flags);
            s.commit(pending.getIntentSender());
        }
    }
}
