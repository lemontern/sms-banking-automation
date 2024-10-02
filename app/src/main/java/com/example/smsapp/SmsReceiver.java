package com.example.smsapp;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.telephony.SmsMessage;
import android.util.Log;
import java.io.FileOutputStream;
import java.io.IOException;

public class SmsReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        Bundle bundle = intent.getExtras();
        if (bundle != null) {
            Object[] pdus = (Object[]) bundle.get("pdus");
            String format = intent.getStringExtra("format");

            if (pdus != null) {
                for (Object pdu : pdus) {
                    SmsMessage smsMessage = SmsMessage.createFromPdu((byte[]) pdu, format);
                    String sender = smsMessage.getDisplayOriginatingAddress();
                    String messageBody = smsMessage.getMessageBody();
                    logSms(context, sender, messageBody);
                }
            }
        }
    }

    private void logSms(Context context, String sender, String messageBody) {
        Log.i("SmsReceiver", "Сообщение от: " + sender + ", текст: " + messageBody);
        try {
            FileOutputStream fos = context.openFileOutput("sms_logs.txt", Context.MODE_APPEND);
            fos.write(("Сообщение от: " + sender + ", текст: " + messageBody + "\n").getBytes());
            fos.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
