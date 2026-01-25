using UnityEngine;

public class RainIntensityController : MonoBehaviour
{
    [Header("Target Particles")]
    public ParticleSystem rainSystem; 

    [Header("Intensity Control")]
    [Range(0f, 1f)]
    public float rainIntensity = 0.5f;

    [Header("Max Limits")]
    public float maxEmission = 500f; 
    public float maxSpeed = 20f;     

    void Update()
    {
        if (rainSystem == null) return;

        // Change Amount
        var emission = rainSystem.emission;
        emission.rateOverTime = rainIntensity * maxEmission;

        // Change Speed
        var main = rainSystem.main;
        main.startSpeed = Mathf.Lerp(2f, maxSpeed, rainIntensity);
        
        // Change Gravity (makes heavy rain feel heavier)
        main.gravityModifier = Mathf.Lerp(1f, 5f, rainIntensity);
    }
}