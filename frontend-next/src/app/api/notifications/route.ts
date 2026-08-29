// app/api/notifications/route.ts

import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { DJANGO_API_ENDPOINT } from "@/config/defaults";


async function getAuthHeaders() {
  const cookieStore = await cookies();

  const token = cookieStore.get("access_token")?.value;


  return {
    ...(token
      ? {
          Authorization: `Bearer ${token}`,
        }
      : {}),
  };
}



async function parseResponse(response: Response) {
  const text = await response.text();

  if (!text) {
    return null;
  }


  try {
    return JSON.parse(text);
  } catch {
    return {
      detail: text,
    };
  }
}



// ==========================================
// GET - Notifications list
// ==========================================

export async function GET(
  request: NextRequest
) {

  try {

    const searchParams =
      request.nextUrl.searchParams;


    const limit =
      searchParams.get("limit") ?? "20";


    const offset =
      searchParams.get("offset") ?? "0";


    const headers =
      await getAuthHeaders();



    const response =
      await fetch(
        `${DJANGO_API_ENDPOINT}/notifications/?limit=${limit}&offset=${offset}`,
        {
          method:"GET",

          headers:{
            Accept:"application/json",
            ...headers,
          },

          cache:"no-store",
        }
      );


    const data =
      await parseResponse(response);



    return NextResponse.json(
      data,
      {
        status:response.status,
      }
    );


  } catch(error){

    console.error(
      "GET /notifications error:",
      error
    );


    return NextResponse.json(
      {
        detail:"Server xatosi"
      },
      {
        status:500
      }
    );

  }

}



// ==========================================
// POST - Mark as read
// ==========================================

export async function POST(
 request:NextRequest
){

 try {


  const body =
    await request.json();



  const headers =
    await getAuthHeaders();



  const response =
    await fetch(
      `${DJANGO_API_ENDPOINT}/notifications/read/`,
      {

       method:"POST",

       headers:{
        "Content-Type":"application/json",
        Accept:"application/json",
        ...headers,
       },


       body:JSON.stringify(body),

       cache:"no-store",

      }
    );



  const data =
    await parseResponse(response);



  return NextResponse.json(
    data,
    {
      status:response.status,
    }
  );



 } catch(error){


  console.error(
    "POST /notifications error:",
    error
  );


  return NextResponse.json(
    {
      detail:"Server xatosi"
    },
    {
      status:500
    }
  );


 }

}



// ==========================================
// DELETE - Clear notifications
// ==========================================

export async function DELETE(){

 try {


  const headers =
    await getAuthHeaders();



  const response =
    await fetch(
      `${DJANGO_API_ENDPOINT}/notifications/`,
      {

       method:"DELETE",

       headers:{
        Accept:"application/json",
        ...headers,
       },


       cache:"no-store",

      }
    );



  const data =
    await parseResponse(response);



  return NextResponse.json(
    data,
    {
      status:response.status,
    }
  );



 } catch(error){


  console.error(
    "DELETE /notifications error:",
    error
  );


  return NextResponse.json(
    {
      detail:"Server xatosi"
    },
    {
      status:500
    }
  );

 }

}