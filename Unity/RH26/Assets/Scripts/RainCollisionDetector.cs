using UnityEngine;

public class RainCollisionDetector : MonoBehaviour
{


    void OnCollisionEnter(Collision other)
    {
        print("In contact with " + other.transform.name);
    }



    void OnCollisionExit(Collision other)
    {
        print("No longer in contact with " + other.transform.name);
    }

}