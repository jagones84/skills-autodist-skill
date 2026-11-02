plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}
android {
    namespace = "com.example.pomodoro"
    compileSdk = 36
    defaultConfig { applicationId="com.example.pomodoro"; minSdk=24; targetSdk=36; versionCode=1; versionName="1.0" }
    buildTypes {
        release { isMinifyEnabled = false }
        getByName("debug") { isDebuggable = true }
    }
    compileOptions { sourceCompatibility=JavaVersion.VERSION_17; targetCompatibility=JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
}
dependencies { implementation(libs.androidx.core.ktx); implementation(libs.androidx.appcompat); implementation(libs.material) }
