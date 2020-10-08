# Connectivity

Documentation of the connectivity module.

## NetworkType

The networkType variable uses numeric codes, see table for description of these codes.
Based on [these docs](https://docs.microsoft.com/en-us/dotnet/api/android.telephony.networktype?view=xamarin-android-sdk-9) [TO CHECK].

| Network Type | Code |
| --- | --- |
| Unknown |	0 |
| Gprs |	1 |
| Edge |	2 |
| Umts |	3 |
| Cdma |	4 |
| Evdo0 |	5 |
| EvdoA |	6 |
| OneXrtt |	7 |
| Hsdpa |	8 |
| Hsupa |	9 |
| Hspa |	10 |
| Iden |	11 |
| EvdoB |	12 |
| Lte |	13 |
| Ehrpd |	14 |
| Hspap |	15 |
| Gsm |	16 |
| TdScdma |	17 |
| Iwlan |	18 |

## networkLevel

Retrieve an abstract level value for the overall signal strength.
> a single integer from 0 to 4 representing the general signal quality. 
> This may take into account many different radio technology inputs.
> 0 represents very poor signal strength while 4 represents a very strong signal strength.


[docs](https://developer.android.com/reference/android/telephony/SignalStrength#getLevel())

| Network Level | Code |
| --- | --- |
| Very poor |	0 |
| Poor |	1 |
| Mediocre | 2 |
| Good |	3 |
| Very Good |	4 |
