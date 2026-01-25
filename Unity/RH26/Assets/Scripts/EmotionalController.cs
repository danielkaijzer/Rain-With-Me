using UnityEngine;

public class EmotionalController : MonoBehaviour
{
    [Header("Input Coordinates (0 to 1)")]
    [Range(0f, 1f)] public float stressLevel;
    [Range(0f, 1f)] public float happinessLevel;

    [Header("Threshold Settings")]
    [Tooltip("Rain starts when happiness falls below this value.")]
    public float happinessThreshold = 0.5f;

    [Header("References")]
    public ParticleSystem rainParticles;

    private void Update()
    {
        UpdateWeather();
    }

    void UpdateWeather()
    {
        // 1. Check if it should be raining
        // If happiness is below the threshold, rain is active.
        bool isRaining = happinessLevel < happinessThreshold;

        if (!isRaining)
        {
            if (rainParticles.isPlaying) rainParticles.Stop();
            return;
        }

        if (!rainParticles.isPlaying) rainParticles.Play();

        // 2. Calculate "Sadness Intensity" (Inverts happiness)
        // If H is 0.2, sadness is 0.8. If H is 0.4, sadness is 0.6.
        float sadnessIntensity = 1f - happinessLevel;

        var main = rainParticles.main;
        var emission = rainParticles.emission;

        // 3. Stress Affects Speed
        // High stress = fast, frantic rain. Low stress = slow, drifting rain.
        main.startSpeed = Mathf.Lerp(2f, 25f, stressLevel);

        // 4. Sadness Affects Size
        // Lower happiness = larger, heavier-looking drops.
        main.startSize = Mathf.Lerp(0.05f, 0.4f, sadnessIntensity);

        // 5. Combined Intensity Affects Density (Rate)
        // We multiply them so that the absolute "worst" state (1.0 stress, 0.0 happiness) 
        // results in the thickest downpour.
        float totalIntensity = sadnessIntensity * stressLevel;
        emission.rateOverTime = Mathf.Lerp(20f, 1000f, totalIntensity);
    }
}