"use client";


import {useEffect,useState} from "react";

import submissionTracker,{
 type TrackedSubmission
} from "@/lib/submissions/tracker";


export function useSubmissionTracker(){

 const [submission,setSubmission]=useState<
 TrackedSubmission|null
 >(
   ()=>submissionTracker.get()
 );


 useEffect(()=>{

   return submissionTracker.subscribe(
     setSubmission
   );


 },[]);



 return submission;

}