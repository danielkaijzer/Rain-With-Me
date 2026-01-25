using UnityEngine;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Collections.Generic; // Added for HashSet

public class CollisionDetector : MonoBehaviour
{
    [Header("Network Settings")]
    public string ipAddress = "127.0.0.1";
    public int sendPort = 5016;

    // We use a HashSet to track unique colliders so we don't double-count the same finger
    private HashSet<Collider> activeHandColliders = new HashSet<Collider>();
    
    private UdpClient udpClient;
    private IPEndPoint remoteEndPoint;

    void Start()
    {
        udpClient = new UdpClient();
        remoteEndPoint = new IPEndPoint(IPAddress.Parse(ipAddress), sendPort);
    }

    void Update()
    {
        // If the count is > 0, at least part of a hand is inside
        bool isHandInside = activeHandColliders.Count > 0;
        
        string message = isHandInside ? "1" : "0";
        Debug.Log($"Hand Inside: {isHandInside} (Count: {activeHandColliders.Count})");
        
        SendData(message);
    }

    private void OnTriggerEnter(Collider other)
    {
        // Check if the object or its parent is a hand
        if (other.name.Contains("Hand") || other.transform.root.name.Contains("Hand"))
        {
            if (!activeHandColliders.Contains(other))
            {
                activeHandColliders.Add(other);
            }
        }
    }

    private void OnTriggerExit(Collider other)
    {
        if (activeHandColliders.Contains(other))
        {
            activeHandColliders.Remove(other);
        }
    }

    private void SendData(string message)
    {
        try
        {
            byte[] data = Encoding.UTF8.GetBytes(message);
            udpClient.Send(data, data.Length, remoteEndPoint);
        }
        catch (System.Exception e)
        {
            Debug.LogError($"UDP Send Error: {e.Message}");
        }
    }

    private void OnApplicationQuit()
    {
        if (udpClient != null) udpClient.Close();
    }
}